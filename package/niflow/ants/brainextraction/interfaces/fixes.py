# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from __future__ import absolute_import, division, print_function, unicode_literals
import os

import numpy as np
import nibabel as nb

from .. import __version__

from nipype.interfaces.ants.resampling import ApplyTransforms
from nipype.interfaces.ants.registration import Registration

from nipype import logging
LOG = logging.getLogger('nipype.interface')


def _copyxform(ref_image, out_image, message=None):
    # Read in reference and output
    # Use mmap=False because we will be overwriting the output image
    resampled = nb.load(out_image, mmap=False)
    orig = nb.load(ref_image)

    if not np.allclose(orig.affine, resampled.affine):
        LOG.debug(
            'Affines of input and reference images do not match, '
            'FMRIPREP will set the reference image headers. '
            'Please, check that the x-form matrices of the input dataset'
            'are correct and manually verify the alignment of results.')

    # Copy xform infos
    qform, qform_code = orig.header.get_qform(coded=True)
    sform, sform_code = orig.header.get_sform(coded=True)
    header = resampled.header.copy()
    header.set_qform(qform, int(qform_code))
    header.set_sform(sform, int(sform_code))
    header['descrip'] = 'xform matrices modified by %s.' % (message or '(unknown)')

    newimg = resampled.__class__(resampled.get_data(), orig.affine, header)
    newimg.to_filename(out_image)


class FixHeaderApplyTransforms(ApplyTransforms):
    """
    A replacement for nipype.interfaces.ants.resampling.ApplyTransforms that
    fixes the resampled image header to match the xform of the reference
    image
    """

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        # Run normally
        runtime = super(FixHeaderApplyTransforms, self)._run_interface(
            runtime, correct_return_codes)

        _copyxform(self.inputs.reference_image,
                   os.path.abspath(self._gen_filename('output_image')),
                   message='%s (niflow.ants.brainextraction v%s)' % (
                       self.__class__.__name__, __version__))
        return runtime


class FixHeaderRegistration(Registration):
    """
    A replacement for nipype.interfaces.ants.registration.Registration that
    fixes the resampled image header to match the xform of the reference
    image
    """

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        # Run normally
        runtime = super(FixHeaderRegistration, self)._run_interface(
            runtime, correct_return_codes)

        # Forward transform
        out_file = self._get_outputfilenames(inverse=False)
        if out_file is not None and out_file:
            _copyxform(
                self.inputs.fixed_image[0], os.path.abspath(out_file),
                message='%s (niworkflows v%s)' % (
                    self.__class__.__name__, __version__))

        # Inverse transform
        out_file = self._get_outputfilenames(inverse=True)
        if out_file is not None and out_file:
            _copyxform(
                self.inputs.moving_image[0], os.path.abspath(out_file),
                message='%s (niworkflows v%s)' % (
                    self.__class__.__name__, __version__))

        return runtime
