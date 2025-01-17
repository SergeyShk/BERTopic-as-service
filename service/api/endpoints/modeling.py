from typing import Any, Dict, List

import numpy as np
from aiobotocore.session import ClientCreatorContext
from bertopic import BERTopic
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.routing import APIRouter
from sqlmodel.ext.asyncio.session import AsyncSession

from ... import crud
from ...models import models
from ...schemas.base import (
    DocsWithPredictions,
    FitResult,
    Input,
    ModelId,
    ModelPrediction,
    PredictIn,
)
from ...schemas.bertopic_wrapper import BERTopicWrapper
from .. import deps
from ..utils import get_sample_dataset, load_model, save_model

router = APIRouter(prefix="/modeling", tags=["modeling"])


def gather_topics(topic_model: BERTopic) -> List[Dict[str, Any]]:
    topic_info = topic_model.get_topics()
    topics = []
    for topic_index, top_words in topic_info.items():
        topics.append(
            {
                "name": topic_model.topic_labels_[topic_index],
                "count": topic_model.topic_sizes_[topic_index],
                "topic_index": topic_index,
                "top_words": [{"name": w[0], "score": w[1]} for w in top_words],
            }
        )
    return topics


@router.post("/training", summary="Run topic modeling", response_model=FitResult)
async def fit(
    data: Input,
    s3: ClientCreatorContext = Depends(deps.get_s3),
    session: AsyncSession = Depends(deps.get_db_async),
) -> FitResult:
    params = dict(data)
    texts = params.pop("texts")
    topic_model = BERTopicWrapper(**params).model
    if texts:
        topics, probs = topic_model.fit_transform(texts)
    else:
        docs = get_sample_dataset()
        predicted_topics, probs = topic_model.fit_transform(docs)

    model_id = await save_model(s3, topic_model)
    model = await crud.topic_model.create(session, obj_in=models.TopicModelBase(model_id=model_id))
    topics = gather_topics(topic_model)
    await crud.topic.save_topics(session, topics=topics, model=model)

    return FitResult(
        model=ModelId(
            model_id=model_id,
        ),
        predictions=ModelPrediction(topics=predicted_topics, probabilities=probs.tolist()),
    )


@router.post(
    "/{model_id}/predicting",
    summary="Predict with existing model",
    response_model=ModelPrediction,
)
async def predict(
    data: PredictIn,
    s3: ClientCreatorContext = Depends(deps.get_s3),
) -> ModelPrediction:
    topic_model = await load_model(s3, data.model.model_id, data.model.version)
    topic_model.calculate_probabilities = data.calculate_probabilities
    topics, probabilities = topic_model.transform(data.texts)
    print(probabilities)
    if data.calculate_probabilities:
        probabilities = probabilities.tolist()
    else:
        probabilities = None
    return ModelPrediction(topics=topics, probabilities=probabilities)


@router.post(
    "/{model_id}/reducting",
    summary="Reduce number of topics in existing model",
    response_model=FitResult,
)
async def reduce_topics(
    data: DocsWithPredictions,
    s3: ClientCreatorContext = Depends(deps.get_s3),
    session: AsyncSession = Depends(deps.get_db_async),
) -> FitResult:
    topic_model = await load_model(s3, data.model.model_id, data.model.version)
    if len(topic_model.get_topics()) < data.num_topics:
        raise HTTPException(
            status_code=400, detail=f"num_topics must be less than {len(topic_model.get_topics())}"
        )

    if len(data.texts) == 0:
        data.texts = get_sample_dataset()
    predicted_topics, probs = topic_model.reduce_topics(
        docs=data.texts,
        topics=data.topics,
        probabilities=np.array(data.probabilities),
        nr_topics=data.num_topics,
    )
    current_max_version = await crud.topic_model.get_max_version(
        session, model_id=data.model.model_id
    )

    model_id = await save_model(s3, topic_model, data.model.model_id, current_max_version + 1)

    model = await crud.topic_model.create(
        session, obj_in=models.TopicModelBase(model_id=model_id, version=current_max_version + 1)
    )
    topics = gather_topics(topic_model)
    await crud.topic.save_topics(session, topics=topics, model=model)

    return FitResult(
        model=ModelId(
            model_id=model_id,
            version=current_max_version + 1,
        ),
        predictions=ModelPrediction(topics=predicted_topics, probabilities=probs.tolist()),
    )
