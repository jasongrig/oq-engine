#  -*- coding: utf-8 -*-
#  vim: tabstop=4 shiftwidth=4 softtabstop=4

#  Copyright (c) 2017, GEM Foundation

#  OpenQuake is free software: you can redistribute it and/or modify it
#  under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  OpenQuake is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.

#  You should have received a copy of the GNU Affero General Public License
#  along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

"""This module provides the classes
:class:`ClassicalLossCurveExporter` and
:class:`EventBasedLossCurveExporter` to export loss curves from the
datastore. Each instance has a method `.export(export_type, what)`
rlzi=None)` to export the data of a given asset in the given export
type and a method `.export_sid(sid, export_type, rlzi=None)` to export
the data of all assets on the given site ID. If the realization index
`rlzi` is given only the data for the chose realization are exported,
otherwise the data for all realizations are exported.

"""
import abc
from openquake.baselib.python3compat import with_metaclass
from openquake.baselib.general import get_array
from openquake.commonlib import writers


class BaseLossCurveExporter(with_metaclass(abc.ABCMeta)):
    """
    Abstract Base Class with common methods for its subclasses
    """
    def __init__(self, dstore):
        self.dstore = dstore
        self.assetcol = dstore['assetcol']
        self.str2asset = {
            aref: self.assetcol[aid]
            for (aid, aref) in enumerate(self.dstore['asset_refs'])}
        self.loss_types = dstore.get_attr('composite_risk_model', 'loss_types')

    @abc.abstractmethod
    def export(self, assert_ref, export_type, rlzi=None):
        pass

    def parse(self, what):
        """
        :param what:
            can be 'asset1/rlz-1', 'sid-1/rlz-2', ...
        """
        splits = what.split('/')
        spec = splits[0]
        if len(splits) == 1:
            rlzi = None
        elif len(splits) == 2:
            rlzi = int(splits[1][4:])
        else:
            raise ValueError('Wrong specification: %s' % what)
        if spec.startswith('sid-'):  # passed the site ID
            sid = int(spec[4:])
            aids = list(get_array(self.assetcol.array, site_id=sid)['idx'])
        else:  # passed the asset name
            aids = [self.str2asset[spec].ordinal]
        arefs = self.dstore['asset_refs'][aids]
        return aids, arefs, spec, rlzi

    def export_csv(self, spec, asset_refs, curves_by_rlzi):
        """
        :param asset_ref: name of the asset
        :param curves_by_rlzi: a dictionary rlzi -> loss curve record
        """
        writer = writers.CsvWriter(fmt=writers.FIVEDIGITS)
        for rlzi in sorted(curves_by_rlzi):
            recs = curves_by_rlzi[rlzi]
            data = [['asset', 'loss_type', 'loss', 'poe']]
            for loss_type in self.loss_types:
                array = recs[loss_type]
                for aref, losses, poes in zip(
                        asset_refs, array['losses'], array['poes']):
                    for loss, poe in zip(losses, poes):
                        data.append((aref, loss_type, loss, poe))
            dest = self.dstore.build_fname(
                'loss_curves', '%s-rlz-%03d' % (spec, rlzi), 'csv')
            writer.save(data, dest)
        return writer.getsaved()


class ClassicalLossCurveExporter(BaseLossCurveExporter):

    def export_curves_by_rlzi(self, aids, rlzi=None):
        """
        :returns: a dictionary rlzi -> record of dtype loss_curve_dt
        """
        data = self.dstore['loss_curves-rlzs'][aids]  # shape (A, R)
        return {rlzi: data[:, rlzi]} if rlzi else dict(enumerate(data.T))

    def export(self, export_type, what):
        """
        :param export_type: 'csv', 'json', ...
        :param what: string describing what to export
        :returns: list of exported file names
        """
        aids, arefs, spec, rlzi = self.parse(what)
        curves = self.export_curves_by_rlzi(aids, rlzi)
        return getattr(self, 'export_' + export_type)(spec, arefs, curves)


class EventBasedLossCurveExporter(BaseLossCurveExporter):
    """Not implemented yet"""

    def export(self, assert_ref, export_type, rlzi=None):
        pass
