# -*- coding: utf-8 -*-
# Copyright 2018 The Blueoil Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
import tensorflow_datasets as tfds


class ObjectDetectionBuilder(tfds.core.GeneratorBasedBuilder):
    """
    A custom TFDS builder for object detection dataset.
    This class loads data from existing dataset classes and
    generate TFDS formatted dataset which is equivalent to the original one.
    See also: https://www.tensorflow.org/datasets/add_dataset
    """

    VERSION = tfds.core.Version("0.1.0")

    def __init__(self, dataset_name, dataset_class=None, dataset_kwargs=None, **kwargs):
        self.name = dataset_name
        self.dataset_class = dataset_class
        self.dataset_kwargs = dataset_kwargs
        super().__init__(**kwargs)

    def _info(self):
        return tfds.core.DatasetInfo(
            builder=self,
            description="Custom TFDS dataset for object detection",
            features=tfds.features.FeaturesDict({
                "image": tfds.features.Image(),
                "objects": tfds.features.Sequence({
                    "label": tfds.features.ClassLabel(),
                    "bbox": tfds.features.BBoxFeature(),
                }),
            }),
        )

    def _split_generators(self, dl_manager):
        self.info.features["objects"]["label"].names = self.dataset_class(**self.dataset_kwargs).classes

        predefined_names = {
            "train": tfds.Split.TRAIN,
            "validation": tfds.Split.VALIDATION,
            "test": tfds.Split.TEST,
        }

        splits = []
        for subset in self.dataset_class.available_subsets:
            dataset = self.dataset_class(subset=subset, **self.dataset_kwargs)
            splits.append(
                tfds.core.SplitGenerator(
                    name=predefined_names.get(subset, subset),
                    num_shards=self._num_shards(dataset),
                    gen_kwargs=dict(dataset=dataset)
                )
            )

        return splits

    def _generate_examples(self, dataset):
        for i, (image, annotations) in enumerate(dataset):
            height, width, _ = image.shape

            objects = [
                {
                    "label": label,
                    "bbox": tfds.features.BBox(
                        ymin / height,
                        xmin / width,
                        min((ymin + h) / height, 1.0),
                        min((xmin + w) / width, 1.0),
                    )
                }
                for xmin, ymin, w, h, label in annotations
                if label != -1
            ]

            yield i, {
                "image": image,
                "objects": objects
            }

    def _num_shards(self, dataset):
        """Decide a number of shards so as not the size of each shard exceeds 256MiB"""
        max_shard_size = 256 * 1024 * 1024  # 256MiB
        total_size = sum(image.nbytes for image, _ in dataset)
        return (total_size + max_shard_size - 1) // max_shard_size
