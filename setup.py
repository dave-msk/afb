# Copyright 2020 (David) Siu-Kei Muk. All Rights Reserved.
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
# ==============================================================================
import setuptools

with open("README.md", "r") as fh:
  long_description = fh.read()

setuptools.setup(
  name="afb",
  version="1.4.0",
  author="(David) Siu-Kei Muk",
  author_email="muksiukei@gmail.com",
  license="Apache 2.0",
  description="Abstract factory broker for object graph construction.",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/dave-msk/afb",
  packages=setuptools.find_packages(exclude=("afb.ext",)),
  download_url="https://github.com/dave-msk/broker/archive/v1.4.0.tar.gz",
  keywords=["afb", "factory", "abstract factory", "config"],
  classifiers=[],
  install_requires=[
      "pyyaml", "deprecated",
  ]
)
