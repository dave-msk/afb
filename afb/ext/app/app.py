from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging
import os
import sys

from afb.core import broker as brk_lib
from afb.ext.app import _registry
from afb.ext.app import job as job_lib
from afb.ext.app import values as val_lib
from afb.utils import general as gen_utils
from afb.utils import decorators as dc


class App(object):
  def __init__(self,
               script_path,
               broker,
               basic_log_fmt=None):
    if not isinstance(broker, brk_lib.Broker) or not callable(broker):
      raise TypeError("`broker` must either be a `Broker` or a zero-argument "
                      "function that returns a `Broker`. Given: {}"
                      .format(broker))
    self._maybe_broker = broker
    self._script_name = os.path.basename(script_path)
    self._basic_log_fmt = gen_utils.val_or_default(
        basic_log_fmt,
        "%(levelname)s: %(asctime)s - %(name)s [#%(thread)d]: %(message)s")

  def run(self):
    docs_dir, run_config = self._parse_args()
    self._generate_docs(docs_dir)
    self._run_jobs(run_config)

  @dc.lazyprop
  def _broker(self):
    # 1. Create and validate given `Broker`.
    user_broker = self._maybe_broker
    if callable(user_broker):
      user_broker = user_broker()
    if not isinstance(user_broker, brk_lib.Broker):
      raise TypeError("`broker` must either be a `Broker` or a zero-argument "
                      "function that returns a `Broker`. Given: {}"
                      .format(user_broker))

    # 2. Create app-specific `Broker`.
    app_brk = _registry.create_broker()

    # 3. Create new broker that merges both
    broker = brk_lib.Broker()
    broker.merge("", user_broker)
    broker.merge("afb/app", app_brk)

    return broker

  @dc.lazyprop
  def _logger(self):
    return logging.getLogger(self._script_name)

  def _parse_args(self):
    parser = argparse.ArgumentParser(prog=self._script_name)
    parser.add_argument("-r", "--run", dest="run_config", metavar="run_config",
                        type=str, default=None,
                        help="Run the jobs with configuration specified in "
                             "<run_config>.")
    parser.add_argument("-d", "--docs", dest="docs_dir", metavar="docs_dir",
                        type=str, default=None,
                        help="Generate documentations in the directory "
                             "specified by <docs_dir>.")
    parser.add_argument(
        "-l", "--log_level", dest="logging_level", type=str, default="INFO",
        metavar="logging_level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging level of execution.")
    flags = parser.parse_args()
    docs_dir, run_config = flags.docs_dir, flags.run_config
    if run_config is None and docs_dir is None:
      parser.print_help()
      sys.exit(0)

    logging.basicConfig(format=self._basic_log_fmt,
                        level=getattr(logging, flags.logging_level))

    return docs_dir, run_config

  def _generate_docs(self, docs_dir):
    if docs_dir is None: return
    self._logger.info("Exporting docs to \"{}\" ...".format(docs_dir))
    self._broker.export_markdown(docs_dir)
    self._logger.info("Exported docs to \"{}\" successfully!".format(docs_dir))

  def _run_jobs(self, run_config):
    if run_config is None: return
    # 1. Create object specs for `Job`s
    # TODO: Try catch
    job_specs = self._broker.make(val_lib.Values,
                                  {"from_config": {"config": run_config}})

    # 2. Instantiate `Job`s from object specs.
    # TODO: Try catch
    jobs = []
    for spec in job_specs:
      job = self._broker.make(job_lib.Job, spec)
      jobs.append(job)

    # 3. Run `Job`s
    for job in jobs:
      # TODO: Try catch
      job.run()
