# nhlib: A New Hazard Library
# Copyright (C) 2012 GEM Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from nhlib.geo.point import Point
from nhlib.geo.line import Line
from nhlib.geo.surface.complex_fault import ComplexFaultSurface

from tests.geo.surface import _utils as utils


class ComplexFaultSurfaceCheckFaultDataTestCase(utils.SurfaceTestCase):
    def test_one_edge(self):
        edges = [Line([Point(0, 0), Point(0, 1)])]
        self.assertRaises(ValueError, ComplexFaultSurface.from_fault_data,
                          edges, mesh_spacing=1)

    def test_one_point_in_an_edge(self):
        edges = [Line([Point(0, 0), Point(0, 1)]),
                 Line([Point(0, 0, 1), Point(0, 1, 1)]),
                 Line([Point(0, 0, 2)])]
        self.assertRaises(ValueError, ComplexFaultSurface.from_fault_data,
                          edges, mesh_spacing=1)

    def test_non_positive_mesh_spacing(self):
        edges = [Line([Point(0, 0), Point(0, 1)]),
                 Line([Point(0, 0, 1), Point(0, 1, 1)])]
        self.assertRaises(ValueError, ComplexFaultSurface.from_fault_data,
                          edges, mesh_spacing=0)
        self.assertRaises(ValueError, ComplexFaultSurface.from_fault_data,
                          edges, mesh_spacing=-1)


class ComplexFaultFromFaultDataTestCase(utils.SurfaceTestCase):
    def test_1(self):
        edge1 = Line([Point(0, 0), Point(0.03, 0)])
        edge2 = Line([Point(0, 0, 2.224), Point(0.03, 0, 2.224)])
        surface = ComplexFaultSurface.from_fault_data([edge1, edge2],
                                                      mesh_spacing=1.112)
        self.assertIsInstance(surface, ComplexFaultSurface)
        self.assert_mesh_is(surface=surface, expected_mesh=[
            [(0, 0, 0), (0.01, 0, 0), (0.02, 0, 0), (0.03, 0, 0)],
            [(0, 0, 1.112), (0.01, 0, 1.112),
             (0.02, 0, 1.112), (0.03, 0, 1.112)],
            [(0, 0, 2.224), (0.01, 0, 2.224),
             (0.02, 0, 2.224), (0.03, 0, 2.224)],
        ])

    def test_2(self):
        edge1 = Line([Point(0, 0, 1), Point(0, 0.02, 1)])
        edge2 = Line([Point(0.02, 0, 0.5), Point(0.02, 0.01, 0.5)])
        edge3 = Line([Point(0, 0, 2), Point(0, 0.02, 2)])
        surface = ComplexFaultSurface.from_fault_data([edge1, edge2, edge3],
                                                      mesh_spacing=1)
        self.assert_mesh_is(surface=surface, expected_mesh=[
         [(0.00000000e+00, 0.00000000e+00, 1.00000000e+00),
          (0.00000000e+00, 1.00000000e-02, 1.00000000e+00),
          (0.00000000e+00, 2.00000000e-02, 1.00000000e+00)],

         [(9.54629388e-03, 5.84522604e-19, 7.61342653e-01),
          (9.27439990e-03, 7.68140016e-03, 7.68140004e-01),
          (8.57984833e-03, 1.57100762e-02, 7.85503798e-01)],

         [(1.90925878e-02, 1.16904519e-18, 5.22685306e-01),
          (1.85487997e-02, 5.36280012e-03, 5.36280008e-01),
          (1.71596963e-02, 1.14201520e-02, 5.71007595e-01)],

         [(1.10611540e-02, 1.66081242e-18, 1.14412831e+00),
          (1.07302090e-02, 7.31744788e-03, 1.15325942e+00),
          (9.88863358e-03, 1.50556836e-02, 1.17651328e+00)],

         [(3.02972015e-03, 2.15257962e-18, 1.76557132e+00),
          (2.91161824e-03, 9.27209551e-03, 1.77023884e+00),
          (2.61757060e-03, 1.86912149e-02, 1.78201896e+00)]
        ])
