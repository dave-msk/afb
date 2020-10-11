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
  version="1.4.1",
  author="(David) Siu-Kei Muk",
  author_email="david.muk@protonmail.com",
  license="Apache 2.0",
  description="Abstract factory broker for object graph construction.",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/dave-msk/afb",
  packages=setuptools.find_packages(include=("afb", "afb.*",),
                                    exclude=("afb.ext", "afb.ext.*",)),
  download_url="https://github.com/dave-msk/broker/archive/v1.4.1.tar.gz",
  keywords=["afb", "factory", "abstract factory", "config"],
  classifiers=[
      "Development Status :: 4 - Beta",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: Apache Software License",
      "Operating System :: OS Independent",
      "Programming Language :: Python",
      "Programming Language :: Python :: 2",
      "Programming Language :: Python :: 2.7",
      "Programming Language :: Python :: 3",
      "Programming Language :: Python :: 3.4",
      "Programming Language :: Python :: 3.5",
      "Programming Language :: Python :: 3.6",
      "Programming Language :: Python :: 3.7",
      "Programming Language :: Python :: 3.8",
      "Programming Language :: Python :: 3.9",
      "Topic :: Software Development",
      "Topic :: Software Development :: Libraries",
      "Topic :: Software Development :: Libraries :: Python Modules",
      "Topic :: Software Development :: Object Brokering",
  ],
  install_requires=[
      "pyyaml", "deprecated",
  ],
  python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4",
)
