# inventree-dymo-plugin

[![License: ](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/license/gpl-3-0)
![CI](https://github.com/wolflu05/inventree-dymo-plugin/actions/workflows/ci.yml/badge.svg)

A label printer driver plugin for [InvenTree](https://inventree.org/), which provides support for Dymo Label Writer® printers.

## Compatibility

The following printers are already supported by the driver:

- DYMO Label Writer 450
- DYMO Label Writer 450 Duo (Tape is not supported currently)
- DYMO Label Writer 450 Turbo
- DYMO Label Writer 450 Twin Turbo

## Requirements

Currently only printing over network is supported, so an RAW network socket server needs to be connected to the printer. A raspberry pi zero w is just enough for that job.

The easiest way to set this up, is using cups and configure a RAW printer device in combination with `xinetd` like described in this [blog post](https://nerdig.es/labelwriter-im-netz-teil1/).

## Installation

> [!IMPORTANT]
> This plugin is only compatible with InvenTree>=0.18, for older versions use v1.0.0 of this plugin.

Goto "Admin Center > Plugins > Install Plugin" and enter `inventree-dymo-plugin` as package name.

Then goto "Admin Center > Machines" and create a new machine using this driver.

## Technical working

This driver implements the RAW Dymo LabelWriter® 450 Series commands like described in the [technical reference manual](https://download.dymo.com/dymo/technical-data-sheets/LW%20450%20Series%20Technical%20Reference.pdf) to send the label data to the printer.
