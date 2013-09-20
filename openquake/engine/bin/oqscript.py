#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

"""OpenQuake: software for seismic hazard and risk assessment

It receives its inputs through a configuration file plus input data in .xml
format and stores the results in .xml format.

Available Hazard Analysis

  Classical PSHA
    Input   Source Model Logic Tree
            GMPE Logic Tree

    Output  Hazard maps
            Hazard curves

  Event-Based PSHA
    Input   Source Model Logic Tree
            GMPE Logic Tree

    Output  Ground Motion fields

  Scenario SHA
    Input   Rupture Model

    Output  Ground Motion fields

Available Risk Analysis

  Classical PSHA-based
    Input   Exposure (a value per asset)
            Vulnerability curves (a list of vulnerability functions)
            Seismic hazard input: hazard curves

    Output  A grid of loss-ratio curves
            A grid of loss curves
            A map of losses at each interval

  Probabilistic event-based
    Input   Exposure (a value per asset)
            Vulnerability curves (a list of vulnerability functions)
            Seismic hazard input: sets of ground motion fields

    Output  A grid of loss-ratio curves
            A grid of loss curves
            A map of losses at each interval
            An aggregated loss curve

"""

import argparse
import getpass
import os
import sys

from os.path import abspath
from os.path import dirname
from os.path import expanduser
from os.path import join

from django.core.exceptions import ObjectDoesNotExist

# just in the case that are you using oq-engine from sources
# with the rest of oq libraries installed into the system (or a
# virtual environment) you must set this environment variable
if os.environ.get("OQ_ENGINE_USE_SRCDIR") is not None:
    sys.modules['openquake'].__dict__["__path__"].insert(
        0, join(dirname(dirname(__file__)), "openquake")
    )

from openquake.engine.utils import config

config.abort_if_no_config_available()

try:
    import celeryconfig
except ImportError:
    sys.path.append('/usr/openquake/engine')

try:
    import oqpath
    oqpath.set_oq_path()
except ImportError:
    pass

from openquake.engine.db.models import set_django_settings_module
set_django_settings_module()

import openquake.engine

from openquake.engine import __version__
from openquake.engine import engine
from openquake.engine.db import models
from openquake.engine.export import hazard as hazard_export
from openquake.engine.export import risk as risk_export
from openquake.engine.input import source

HAZARD_OUTPUT_ARG = "--hazard-output-id"
HAZARD_CALCULATION_ARG = "--hazard-calculation-id"
MISSING_HAZARD_MSG = ("Please specify the ID of the hazard output (or "
                      "calculation) to be used by using '%s (or %s) <id>'" %
                      (HAZARD_OUTPUT_ARG, HAZARD_CALCULATION_ARG))


def set_up_arg_parser():
    """Set up and return an :class:`argparse.ArgumentParser` with all of the
    OpenQuake command line options."""
    parser = argparse.ArgumentParser(
        description='OpenQuake Seismic Hazard and Risk Analysis Engine')

    general_grp = parser.add_argument_group('General')
    general_grp.add_argument(
        '--version', action='store_true', help='Display version information')
    general_grp.add_argument(
        '--log-file', '-L',
        help=('Location to store log messages; if not specified, log messages'
              ' will be printed to the console (to stderr)'),
        required=False, metavar='LOG_FILE')
    general_grp.add_argument(
        '--log-level', '-l',
        help='Defaults to "progress"', required=False,
        choices=['debug', 'info', 'progress', 'warn', 'error', 'critical'],
        default='progress')
    general_grp.add_argument(
        '--no-distribute', '--nd', action='store_true',
        help=('Disable calculation task distribution and run the computation'
              ' in a single process. This is intended for use in debugging '
              ' and profiling.')
    )
    general_grp.add_argument(
        '--list-inputs', '--li',
        help='List inputs of a specific input type',
        metavar="INPUT_TYPE")

    general_grp.add_argument(
        '--yes', '-y', action='store_true',
        help='Automatically answer "yes" when asked to confirm an action'
    )
    general_grp.add_argument(
        '--config-file',
        help='Custom openquake.cfg file, to override default configurations',
        metavar='CONFIG_FILE'
    )

    hazard_grp = parser.add_argument_group('Hazard')
    hazard_grp.add_argument(
        '--run-hazard',
        '--rh',
        help='Run a hazard job with the specified config file',
        metavar='CONFIG_FILE')
    hazard_grp.add_argument(
        '--list-hazard-calculations',
        '--lhc',
        help='List hazard calculation information',
        action='store_true')
    hazard_grp.add_argument(
        '--list-hazard-outputs',
        '--lho',
        help='List outputs for the specified hazard calculation',
        metavar='HAZARD_CALCULATION_ID')
    hazard_grp.add_argument(
        '--export-hazard',
        '--eh',
        help='Export the desired output to the specified directory',
        nargs=2, metavar=('OUTPUT_ID', 'TARGET_DIR'))
    hazard_grp.add_argument(
        '--delete-hazard-calculation',
        '--dhc',
        help='Delete a hazard calculation and all associated outputs',
        metavar='HAZARD_CALCULATION_ID')

    risk_grp = parser.add_argument_group('Risk')
    risk_grp.add_argument(
        '--run-risk',
        '--rr',
        help='Run a risk job with the specified config file',
        metavar='CONFIG_FILE')
    risk_grp.add_argument(
        HAZARD_OUTPUT_ARG,
        '--ho',
        help='Use the desired hazard output as input for the risk job',
        metavar='HAZARD_OUTPUT')
    risk_grp.add_argument(
        HAZARD_CALCULATION_ARG,
        '--hc',
        help='Use the desired hazard calculation as input for the risk job',
        metavar='HAZARD_CALCULATION_ID')
    risk_grp.add_argument(
        '--list-risk-calculations',
        '--lrc',
        help='List risk calculation information',
        action='store_true')
    risk_grp.add_argument(
        '--list-risk-outputs',
        '--lro',
        help='List outputs for the specified risk calculation',
        metavar='RISK_CALCULATION_ID')
    risk_grp.add_argument(
        '--export-risk',
        '--er',
        help='Export the desired risk output to the specified directory',
        nargs=2,
        metavar=('OUTPUT_ID', 'TARGET_DIR'))
    risk_grp.add_argument(
        '--delete-risk-calculation',
        '--drc',
        help='Delete a risk calculation and all associated outputs',
        metavar='RISK_CALCULATION_ID')

    export_grp = parser.add_argument_group('Export')
    export_grp.add_argument(
        '--exports', choices=['xml'],  default=[], action="append",
        help=(
            'Use with --run-hazard and --run-risk to automatically export '
            'all calculation results to the specified format. Only "xml" is '
            'supported currently. This is optional. If not specified, '
            'nothing will be exported; results will only be stored in the '
            'database.'
        )
    )
    export_grp.add_argument(
        '--export-type', '--et',
        choices=['xml', 'geojson'],
        default='xml',
        action='store',
        help=('Use with --export-hazard or --export-risk, specify the '
              'desired output format. Defaults to "xml".')
    )

    pre_proc_grp = parser.add_argument_group('Pre-processing')
    pre_proc_grp.add_argument(
        '--optimize-source-model',
        '--osm',
        help=('Optimize a source model by discretizating an area source into'
              ' point sources, given a discretization step (in km)'),
        nargs=3,
        metavar=('INPUT_FILE', 'AREA_DISCRETIZATION', 'OUTPUT_FILE')
    )

    return parser


def list_inputs(input_type):
    """
    Print a list of available input models
    """

    available_input_types = ["exposure"]

    if input_type not in available_input_types:
        engine.complain_and_exit(
            "Wrong input type. Available input types: %s"
            % (", ".join(available_input_types))
        )
    inputs = models.Input.objects.filter(
        input_type=input_type).order_by('-last_update')

    if not inputs.count():
        print "No inputs found of type %s" % input_type
        return
    print ('model id | source path | last update')

    for inp in inputs:
        print "%9d|%s|%12s" % (inp.id, inp.path, inp.last_update)


def list_hazard_calculations():
    """
    Print a summary of past hazard calculations.
    """
    hcs = engine.get_hazard_calculations(getpass.getuser())
    _print_calcs_summary(hcs)


def list_risk_calculations():
    """
    Print a summary of past risk calculations.
    """
    rcs = engine.get_risk_calculations(getpass.getuser())
    _print_calcs_summary(rcs)


def _print_calcs_summary(calcs):
    """
    :param calcs:
        List of :class:`openquake.engine.db.models.HazardCalculation` or
        :class:`openquake.engine.db.models.RiskCalculation` objects.
    """
    if len(calcs) == 0:
        print 'None'
    else:
        print ('calc_id | status | last_update | '
               'description')
        for calc in calcs:
            latest_job = calc.oqjob
            if latest_job.is_running:
                status = 'pending'
            else:
                if latest_job.status == 'complete':
                    status = 'successful'
                else:
                    status = 'failed'
            last_update = latest_job.last_update.strftime(
                '%Y-%m-%d %H:%M:%S %Z'
            )

            print '%s | %s | %s | %s' % (
                calc.id, status, last_update, calc.description
            )


def list_imported_outputs():
    """
    List outputs which were imported from a file, not calculated from a job
    """
    outputs = models.Output.objects.filter(oq_job__isnull=True)
    engine.print_outputs_summary(outputs)


def export_hazard(haz_output_id, target_dir, export_type):
    export(hazard_export.export, haz_output_id, target_dir, export_type)


def export_risk(risk_output_id, target_dir, export_type):
    export(risk_export.export, risk_output_id, target_dir, export_type)


def export(fn, output_id, target_dir, export_type):
    """
    Simple UI wrapper around
    :func:`openquake.engine.export.hazard.export` which prints a summary
    of files exported, if any.
    """
    queryset = models.Output.objects.filter(pk=output_id)
    if not queryset.exists():
        print 'No output found for OUTPUT_ID %s' % output_id
        return

    if queryset.all()[0].oq_job.status != "complete":
        print ("Exporting output produced by a job which did not run "
               "successfully. Results might be uncomplete")

    try:
        the_file = fn(output_id, target_dir, export_type)
        print 'File Exported:'
        print the_file
    except NotImplementedError, err:
        print err.message
        print 'This feature is probably not implemented yet'


def _touch_log_file(log_file):
    """If a log file destination is specified, attempt to open the file in
    'append' mode ('a'). If the specified file is not writable, an
    :exc:`IOError` will be raised."""
    open(abspath(log_file), 'a').close()


def del_haz_calc(hc_id, confirmed=False):
    """
    Delete a hazard calculation and all associated outputs.
    """
    if confirmed or confirm(
            'Are you sure you want to delete this hazard calculation and all '
            'associated outputs?\nThis action cannot be undone. (y/n): '):
        try:
            engine.del_haz_calc(hc_id)
        except RuntimeError, err:
            print err.message


def del_risk_calc(rc_id, confirmed=False):
    """
    Delete a risk calculation and all associated outputs.
    """
    if confirmed or confirm(
            'Are you sure you want to delete this risk calculation and all '
            'associated outputs?\nThis action cannot be undone. (y/n): '):
        try:
            engine.del_risk_calc(rc_id)
        except RuntimeError, err:
            print err.message


def confirm(prompt):
    """
    Ask for confirmation, given a ``prompt`` and return a boolean value.
    """
    while True:
        try:
            answer = raw_input(prompt)
        except KeyboardInterrupt:
            # the user presses ctrl+c, just say 'no'
            return False

        answer = answer.strip().lower()

        if answer not in ('y', 'n'):
            print 'Please enter y or n'
            continue
        return answer == 'y'


def optimize_source_model(input_path, area_src_disc, output_path):
    """
    Read a source model and generate a new one, converting area sources to
    point sources.
    """
    area_src_disc = float(area_src_disc)
    source.optimize_source_model(input_path, area_src_disc,
                                 output_path)
    engine.complain_and_exit(output_path)


def main():
    arg_parser = set_up_arg_parser()

    args = arg_parser.parse_args()

    if args.version:
        engine.complain_and_exit(__version__)

    if args.config_file:
        os.environ[config.OQ_CONFIG_FILE_VAR] = \
            abspath(expanduser(args.config_file))
        config.refresh()

    if args.optimize_source_model:
        optimize_source_model(*args.optimize_source_model)

    if args.no_distribute:
        os.environ[openquake.engine.NO_DISTRIBUTE_VAR] = '1'

    if args.list_inputs:
        list_inputs(args.list_inputs)
    # hazard
    elif args.list_hazard_calculations:
        list_hazard_calculations()
    elif args.list_hazard_outputs is not None:
        engine.list_hazard_outputs(args.list_hazard_outputs)
    elif args.export_hazard is not None:
        output_id, target_dir = args.export_hazard
        output_id = int(output_id)

        export_hazard(output_id, expanduser(target_dir), args.export_type)
    elif args.run_hazard is not None:
        log_file = expanduser(args.log_file) \
            if args.log_file is not None else None
        engine.run_hazard(expanduser(args.run_hazard), args.log_level,
                          log_file, args.exports)
    elif args.delete_hazard_calculation is not None:
        del_haz_calc(args.delete_hazard_calculation, args.yes)
    # risk
    elif args.list_risk_calculations:
        list_risk_calculations()
    elif args.list_risk_outputs is not None:
        engine.list_risk_outputs(args.list_risk_outputs)
    elif args.export_risk is not None:
        output_id, target_dir = args.export_risk
        export_risk(output_id, expanduser(target_dir), args.export_type)
    elif args.run_risk is not None:
        if (args.hazard_output_id is None
                and args.hazard_calculation_id is None):
            engine.complain_and_exit(MISSING_HAZARD_MSG)
        log_file = expanduser(args.log_file) \
            if args.log_file is not None else None
        engine.run_risk(expanduser(args.run_risk), args.log_level, log_file,
                        args.exports, hazard_output_id=args.hazard_output_id,
                        hazard_calculation_id=args.hazard_calculation_id)
    elif args.delete_risk_calculation is not None:
        del_risk_calc(args.delete_risk_calculation, args.yes)

    else:
        arg_parser.print_usage()


if __name__ == '__main__':
    main()
