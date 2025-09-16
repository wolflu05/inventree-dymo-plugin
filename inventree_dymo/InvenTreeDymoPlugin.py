import socket
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from machine.machine_type import BaseDriver
from plugin import InvenTreePlugin
from plugin.mixins import MachineDriverMixin
from plugin.machine.machine_types import LabelPrinterBaseDriver, LabelPrinterMachine
from report.models import LabelTemplate

from .version import DYMO_PLUGIN_VERSION
from .dymo import DymoLabel, RoleSelect, PrintDensity


class InvenTreeDymoPlugin(InvenTreePlugin, MachineDriverMixin):
    AUTHOR = "wolflu05"
    DESCRIPTION = "InvenTree Dymo plugin"
    VERSION = DYMO_PLUGIN_VERSION

    # Machine driver registry is only available in InvenTree 0.14.0 and later
    # Machine driver interface was fixed with 0.16.0 to work inside of inventree workers
    # Machine driver interface was changed with 0.18.0
    MIN_VERSION = "0.18.0"

    TITLE = "InvenTree Dymo Plugin"
    SLUG = "inventree-dymo-plugin"
    NAME = "InvenTree Dymo Plugin"

    def get_machine_drivers(self):
        """Register machine drivers."""
        return [DymoLabelPrinterDriver]


class DymoLabelPrinterDriver(LabelPrinterBaseDriver):
    """Label printer driver for Dymo printers."""

    SLUG = "dymo-driver"
    NAME = "Dymo Driver"
    DESCRIPTION = "Dymo label printing driver for InvenTree"

    def __init__(self, *args, **kwargs):
        self.MACHINE_SETTINGS = {
            'SERVER': {
                'name': _('Server'),
                'description': _('IP/Hostname of the Dymo print server'),
                'default': 'localhost',
                'required': True,
            },
            'PORT': {
                'name': _('Port'),
                'description': _('Port number of the Dymo print server'),
                'validator': int,
                'default': 9100,
                'required': True,
            },
            'SELECT_ROLL': {
                'name': _('Select Roll'),
                'description': _('Select the roll to use for printing'),
                'choices': [(a.name, a.label) for a in RoleSelect],
                'default': 'AUTOMATIC',
                'required': True,
            },
            'DENSITY': {
                'name': _('Print Density'),
                'description': _('Set the print density'),
                'choices': [(a.name, a.label) for a in PrintDensity],
                'default': 'NORMAL',
                'required': True,
            },
            'PRINT_MODE': {
                'name': _('Print Mode'),
                'description': _('Set the print mode'),
                'choices': [('TEXT', _('Text (300x300dpi)')), ('GRAPHIC', _('Graphic (300x600dpi)'))],
                'default': 'TEXT',
                'required': True,
            },
            'LABEL_LENGTH': {
                'name': _('Label Length'),
                'description': _('Set the label length in dots between the holes + 10mm tolerance (e.g: (<distance> mm + 10mm)/25.4inch*300dpi)'),
                'validator': int,
                'default': 3058,
                'required': True,
            },
            'THRESHOLD': {
                'name': _('Threshold'),
                'description': _('Set the threshold for converting grayscale to BW (0-255)'),
                'validator': [int, MinValueValidator(0), MaxValueValidator(255)],
                'default': 200,
                'required': True,
            },
            'ROTATE': {
                'name': _('Rotate'),
                'description': _('Rotate the label'),
                'choices': [(f"{a}", f"{a}°") for a in [0, 90, 180, 270]],
                'default': "0",
                'required': False,
            },
        }

        super().__init__(*args, **kwargs)

    def print_labels(self, machine: LabelPrinterMachine, label: LabelTemplate, items: QuerySet[models.Model], **kwargs):
        """Print labels using a Dymo label printer."""
        printing_options = kwargs.get('printing_options', {})

        dymo_label = DymoLabel(
            label_length=machine.get_setting('LABEL_LENGTH', 'D'),
            mode=machine.get_setting('PRINT_MODE', 'D'),
            density=PrintDensity[machine.get_setting('DENSITY', 'D')],
            role_select=RoleSelect[machine.get_setting('SELECT_ROLL', 'D')],
            rotate=int(machine.get_setting('ROTATE', 'D')),
            threshold=machine.get_setting('THRESHOLD', 'D'),
        )

        for item in items:
            dpi = {"TEXT": 300, "GRAPHIC": 600}[dymo_label.mode]
            png = self.render_to_png(label, item, dpi=dpi)

            for _copies in range(printing_options.get('copies', 1)):
                dymo_label.add_label(png)

        data = dymo_label.get_data()
        self.send_data(machine, data)

    def send_data(self, machine: LabelPrinterMachine, data: bytearray):
        machine.set_status(LabelPrinterMachine.MACHINE_STATUS.UNKNOWN)

        ip_addr = machine.get_setting('SERVER', 'D')
        port = machine.get_setting('PORT', 'D')

        try:
            print_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print_socket.connect((ip_addr, port))
            print_socket.send(data)
            print_socket.close()
        except Exception as e:
            machine.set_status(LabelPrinterMachine.MACHINE_STATUS.DISCONNECTED)
            machine.handle_error(f"Error connecting to network printer: {e}")
