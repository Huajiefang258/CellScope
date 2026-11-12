# Third-party notices

CellScope bundles or depends on the following third-party components. Their
licenses apply to those components; CellScope's own code is GPL-3.0 (see
`LICENSE`).

## Cellpose / Cellpose-SAM

- Project: https://github.com/MouseLand/cellpose
- Copyright © 2020 Howard Hughes Medical Institute
- License: BSD-3-Clause (the `vendor/cp3/cellpose` and `vendor/cp4/cellpose`
  directories are Cellpose source distributions)
- Model weights are distributed by the Cellpose authors under CC-BY-NC. They
  are not included in this repository and are downloaded at the user's request.

BSD-3-Clause notice:

> Redistribution and use in source and binary forms, with or without
> modification, are permitted provided that the following conditions are met:
> redistributions of source code must retain the above copyright notice, this
> list of conditions and the following disclaimer; redistributions in binary
> form must reproduce the above copyright notice, this list of conditions and
> the following disclaimer in the documentation and/or other materials provided
> with the distribution; neither the name of HHMI nor the names of its
> contributors may be used to endorse or promote products derived from this
> software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
> AND ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED. IN NO EVENT SHALL THE
> COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DAMAGES ARISING IN ANY WAY
> OUT OF THE USE OF THIS SOFTWARE.

## PyQt5

- Project: https://riverbankcomputing.com/software/pyqt/
- License: GPL-3.0 or commercial. CellScope is distributed under GPL-3.0 to
  comply with the GPL option.

## ImageJ

- Project: https://imagej.net/ij/
- ImageJ 1.x is developed by NIH. See the ImageJ website for its licensing
  terms. The installer downloads ImageJ 1.54g from the official ImageJ
  distribution site.

## Python packages

The following packages are installed from PyPI at install time and keep their
own licenses:

- PyTorch — BSD-3-Clause — https://pytorch.org
- NumPy — BSD-3-Clause — https://numpy.org
- SciPy — BSD-3-Clause — https://scipy.org
- OpenCV — Apache-2.0 — https://opencv.org
- tifffile — BSD-3-Clause — https://github.com/cgohlke/tifffile
- imagecodecs — BSD-3-Clause — https://github.com/cgohlke/imagecodecs
- fastremap — BSD-3-Clause
- natsort — BSD-3-Clause
- roifile — BSD-3-Clause
- fill-voids — BSD-3-Clause
- segment_anything — Apache-2.0 (Meta)
- tqdm — MPL-2.0 / MIT
- Pillow — HPND

If you redistribute a built package, keep the license texts of the packages
you ship and comply with their terms.
