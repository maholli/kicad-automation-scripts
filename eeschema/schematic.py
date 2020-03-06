#!/usr/bin/env python

#   Copyright 2019 Productize SPRL
#   Copyright 2015-2016 Scott Bezek and the splitflap contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

__author__   ='Scott Bezek, Salvador E. Tropea'
__copyright__='Copyright 2015-2020, INTI/Productize SPRL/Scott Bezek'
__credits__  =['Salvador E. Tropea','Scott Bezek']
__license__  ='Apache 2.0'
__email__    ='salvador@inti.gob.ar'
__status__   ='beta'

import logging
import os
import subprocess
import sys
import time
import re
import argparse

# Look for the 'util' module from where the script is running
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(script_dir))
# Utils import
# Log functionality first
from util import log
log.set_domain(os.path.splitext(os.path.basename(__file__))[0])
from util import file_util
from util.misc import (REC_W,REC_H,__version__)
from util.ui_automation import (
    PopenContext,
    xdotool,
    wait_for_window,
    recorded_xvfb,
    clipboard_store,
    clipboard_retrieve
)

def dismiss_library_error():
    # The "Error" modal pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    # There -should- be a way to disable it, but I haven't the magic to drop in the config file yet
    try:
        nf_title = 'Error'
        wait_for_window(nf_title, nf_title, 3)

        logger.info('Dismiss eeschema library warning modal')
        xdotool(['search', '--onlyvisible', '--name', nf_title, 'windowfocus'])
        xdotool(['key', 'Escape'])
    except RuntimeError:
        pass


def dismiss_library_warning():
    # The "Not Found" window pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    try:
        nf_title = 'Not Found'
        wait_for_window(nf_title, nf_title, 3)

        logger.info('Dismiss eeschema library warning window')
        xdotool(['search', '--onlyvisible', '--name', nf_title, 'windowfocus'])
        xdotool(['key', 'Return'])
    except RuntimeError:
        pass

def dismiss_newer_version():
    # The "Not Found" window pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    try:
        logger.info('Dismiss schematic version notification')
        wait_for_window('Newer schematic version notification', 'Info', 3)

        xdotool(['key', 'Return'])
    except RuntimeError:
        pass


def dismiss_remap_helper():
    # The "Remap Symbols" windows pop up if the uses the project symbol library 
    # the older list look up method for loading library symbols.
    # This can be ignored as we're just trying to output data and don't 
    # want to mess with the actual project.
    try:
        logger.info('Dismiss schematic symbol remapping')
        wait_for_window('Remap Symbols', 'Remap', 3)

        xdotool(['key', 'Escape'])
    except RuntimeError:
        pass


def eeschema_skip_errors():
    #dismiss_newer_version()
    #dismiss_remap_helper();
    #dismiss_library_warning()
    #dismiss_library_error()
    return 0

def eeschema_plot_schematic(output_dir, file_format, all_pages):
    if file_format not in ('pdf', 'svg'):
        raise ValueError("file_format should be 'pdf' or 'svg'")

    clipboard_store(output_dir)

    logger.info('Focus main eeschema window')
    wait_for_window('Eeschema', '.sch')

    xdotool(['search', '--onlyvisible', '--name', '.sch', 'windowfocus'])

    logger.info('Open File->pLot')
    xdotool(['key', 'alt+f',
        'l'
    ])

    wait_for_window('plot', 'Plot')

    logger.info('Paste output directory')
    xdotool(['key', 'ctrl+v'])

    logger.info('Move to the "plot" button')

    command_list = ['key',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
    ]

    if not all_pages:   # all pages is default option
        command_list.extend(['Tab'])
    xdotool(command_list)

    logger.info('Plot')
    xdotool(['key', 'Return'])
    logger.info('Closing window')
    xdotool(['key', 'Escape'])


def eeschema_quit():
    logger.info('Quitting eeschema')
    xdotool(['key', 'Escape', 'Escape', 'Escape'])
    wait_for_window('eeschema', '.sch')
    logger.info('Focus main eeschema window')
    xdotool(['search', '--onlyvisible', '--name', '.sch', 'windowfocus'])
    xdotool(['key', 'Ctrl+q'])


def set_default_plot_option(file_format="hpgl"):
    # eeschema saves the latest plot format, this is problematic because
    # plot_schematic() does not know which option is set (it assumes HPGL)

    logger.info('Setting the default plot format to ' + file_format);
    opt_file_path = os.path.expanduser('~/.config/kicad/')
    in_p = os.path.join(opt_file_path, 'eeschema')
    if os.path.exists(in_p):
        out_p = os.path.join(opt_file_path, 'eeschema.new')
        in_f = open(in_p)
        out_f = open(out_p, 'w')
        for in_line in in_f:
            if in_line.find('=') != -1:
                param, value = in_line.split('=', 1)
            else:
                param = 'none'
                value = 'none'
            if param == 'PlotFormat':
                if file_format == "ps":
                        out_line = 'PlotFormat=1\n'
                elif file_format == "dxf":
                        out_line = 'PlotFormat=3\n'
                elif file_format == "pdf":
                        out_line = 'PlotFormat=4\n'
                elif file_format == "svg":
                        out_line = 'PlotFormat=5\n'
                else: #  if file_format == "hpgl" or we don't know what's up:
                        out_line = 'PlotFormat=0\n'
            else:
                out_line = in_line
            out_f.write(out_line)
        out_f.close()
        os.remove(in_p)
        os.rename(out_p, in_p)

def eeschema_export_schematic(schematic, output_dir, file_format="svg", all_pages=False, screencast_dir=None):
    file_format = file_format.lower()
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(schematic))[0]+'.'+file_format)
    if os.path.exists(output_file):
        logger.debug('Removing old file')
        os.remove(output_file)

    set_default_plot_option(file_format)
    os.path.basename('/root/dir/sub/file.ext')

    with recorded_xvfb(screencast_dir, 'export_eeschema_screencast.ogv', width=1024, height=900, colordepth=24):
        with PopenContext(['eeschema', schematic], close_fds=True, stderr=open(os.devnull, 'wb')) as eeschema_proc:
            eeschema_skip_errors()
            eeschema_plot_schematic(output_dir, file_format, all_pages)
            eeschema_quit()
            eeschema_proc.wait()

    return output_file

def eeschema_parse_erc(erc_file, warning_as_error = False):
    with open(erc_file, 'r') as f:
        lines = f.read().splitlines()
        last_line = lines[-1]
    
    logger.debug('Last line: '+last_line)
    m = re.search('^ \*\* ERC messages: ([0-9]+) +Errors ([0-9]+) +Warnings ([0-9]+)+$', last_line)
    messages = m.group(1)
    errors = m.group(2)
    warnings = m.group(3)

    if warning_as_error:
        return int(errors) + int(warnings)
    return int(errors)

def eeschema_run_erc_schematic(output_dir, pid):

    logger.info('Focus main eeschema window')
    wait_for_window('eeschema', '.sch')

    logger.info('Open Tools->Electrical Rules Checker')
    xdotool(['key',
        'alt+i', # alt+t
        'c'
    ])

    # Do this now since we have to wait for KiCad anyway
    clipboard_store(output_dir)

    logger.info('Focus Electrical Rules Checker window')
    wait_for_window('Electrical Rules Checker', 'Electrical Rules Checker')
    xdotool(['key',
        'Tab',
        'Tab',
        'Tab',
        'Tab',
        'space',
        'Return'
    ])

    wait_for_window('ERC File save dialog', 'ERC File')
    xdotool(['key', 'Home'])
    logger.info('Pasting output dir')
    xdotool(['key', 'ctrl+v'])
    logger.info('Copy full file path')
    xdotool(['key',
        'ctrl+a',
        'ctrl+c'
    ])

    erc_file = clipboard_retrieve()
    if os.path.exists(erc_file):
        os.remove(erc_file)

    logger.info('Run ERC')
    xdotool(['key', 'Return'])

    logger.info('Wait for ERC file creation')
    file_util.wait_for_file_created_by_process(pid, erc_file)

    logger.info('Exit ERC')
    xdotool(['key', 'shift+Tab', 'Return'])

    return erc_file


def eeschema_netlist_commands(output_file, pid):
    logger.info('Focus main eeschema window')
    wait_for_window('eeschema', '.sch')

    logger.info('Open Tools->Generate Netlist File')
    xdotool(['key',
        'alt+t',
        'n'
    ])

    # Do this now since we have to wait for KiCad anyway
    clipboard_store(output_file)

    logger.info('Focus Netlist window')
    wait_for_window('Netlist', 'Netlist')
    xdotool(['key','Tab','Tab','Return'])

    wait_for_window('Netlist File save dialog', 'Save Netlist File')
    logger.info('Pasting output file')
    xdotool(['key', 'ctrl+v'])
    logger.info('Copy full file path')
    xdotool(['key', 'ctrl+a', 'ctrl+c'])

    net_file = clipboard_retrieve()
    if os.path.exists(net_file):
        os.remove(net_file)

    logger.info('Generate Netlist')
    xdotool(['key', 'Return'])

    logger.info('Wait for Netlist file creation')
    file_util.wait_for_file_created_by_process(pid, net_file)

    return net_file


def eeschema_bom_xml_commands(output_file, pid):
    logger.info('Focus main eeschema window')
    wait_for_window('eeschema', '.sch')

    logger.info('Open Tools->Generate Bill of Materials')
    xdotool(['key',
        'alt+t',
        'm'
    ])

    logger.info('Focus BoM window')
    wait_for_window('Bill of Material', 'Bill of Material')
    xdotool(['key','Return'])

    logger.info('Wait for BoM file creation')
    file_util.wait_for_file_created_by_process(pid, output_file)

    time.sleep(3)

    logger.info('Close BoM window')
    xdotool(['key','Tab','Tab','Tab','Tab','Tab','Tab','Tab','Tab','Tab','Return'])
    wait_for_window('eeschema', '.sch')

    return output_file


def eeschema_run_erc(schematic, output_dir, warning_as_error, screencast_dir=None):
    os.environ['EDITOR'] = '/bin/cat'

    with recorded_xvfb(screencast_dir, 'run_erc_eeschema_screencast.ogv', width=1024, height=900, colordepth=24):
        with PopenContext(['eeschema', schematic], close_fds=True, stderr=open(os.devnull, 'wb')) as eeschema_proc:
            eeschema_skip_errors()
            erc_file = eeschema_run_erc_schematic(output_dir,eeschema_proc.pid)
            eeschema_quit()
            eeschema_proc.wait()

    return eeschema_parse_erc(erc_file, warning_as_error)

def eeschema_netlist(schematic, output_dir, screencast_dir=None):
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(schematic))[0])
    with recorded_xvfb(screencast_dir, 'netlist_eeschema_screencast.ogv', width=1600, height=900, colordepth=24):
        with PopenContext(['eeschema', schematic], close_fds=True, stderr=open(os.devnull, 'wb')) as eeschema_proc:
            eeschema_skip_errors()
            eeschema_netlist_commands(output_file,eeschema_proc.pid)
            eeschema_quit()
            eeschema_proc.wait()

def eeschema_bom_xml(schematic, output_dir, screencast_dir=None):
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(schematic))[0]+'.xml')
    with recorded_xvfb(screencast_dir, 'bom_xml_eeschema_screencast.ogv', width=1600, height=900, colordepth=24):
        with PopenContext(['eeschema', schematic], close_fds=True, stderr=open(os.devnull, 'wb')) as eeschema_proc:
            eeschema_skip_errors()
            eeschema_bom_xml_commands(output_file,eeschema_proc.pid)
            eeschema_quit()
            eeschema_proc.wait()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KiCad schematic automation')
    subparsers = parser.add_subparsers(help='Command:', dest='command')

    parser.add_argument('--schematic', help='KiCad schematic file')
    parser.add_argument('--output_dir', help='output directory')

    parser.add_argument('--screencast_dir', help="Directory to record screencast to. If empty, no screencast", default=None)
    parser.add_argument('--verbose','-v',action='count',default=0)
    parser.add_argument('--version','-V',action='version', version='%(prog)s '+__version__+' - '+
                        __copyright__+' - License: '+__license__)

    export_parser = subparsers.add_parser('export', help='Export a schematic')
    export_parser.add_argument('--file_format', '-f', help='Export file format',
        choices=['svg', 'pdf'],
        default='svg'
    )
    export_parser.add_argument('--all_pages', '-a', help='Plot all schematic pages in one file',
        action='store_true'
    )

    erc_parser = subparsers.add_parser('run_erc', help='Run Electrical Rules Checker on a schematic')
    erc_parser.add_argument('--warnings_as_errors', '-w', help='Treat warnings as errors',
        action='store_true'
    )

    netlist_parser = subparsers.add_parser('netlist', help='Create the netlist')
    bom_xml_parser = subparsers.add_parser('bom_xml', help='Create the BoM in XML format')

    args = parser.parse_args()

    # Create a logger with the specified verbosity
    logger = log.init(args.verbose)

    if not os.path.isfile(args.schematic):
        logger.error(args.schematic+' does not exist')
        exit(-1)

    output_dir = os.path.abspath(args.output_dir)+'/'
    file_util.mkdir_p(output_dir)
    os.environ['LANG'] = 'C.UTF-8'

    if args.command == 'export':
        eeschema_export_schematic(args.schematic, output_dir, args.file_format, args.all_pages, args.screencast_dir)
        exit(0)
    if args.command == 'netlist':
        eeschema_netlist(args.schematic, output_dir, args.screencast_dir)
        exit(0)
    if args.command == 'bom_xml':
        eeschema_bom_xml(args.schematic, output_dir, args.screencast_dir)
        exit(0)
    if args.command == 'run_erc':
        errors = eeschema_run_erc(args.schematic, output_dir, args.warnings_as_errors, args.screencast_dir)
        if errors > 0:
            logger.error('{} ERC errors detected'.format(errors))
            exit(errors)
        logger.info('No errors');
        exit(0)
    else:
        usage()
        if sys.argv[1] == 'help':
            exit(0)
    exit(-1)
