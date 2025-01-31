import ast

import typer

from .utils import SDATA_HELPER

app_segmentation = typer.Typer()


@app_segmentation.command()
def cellpose(
    sdata_path: str = typer.Argument(help=SDATA_HELPER),
    diameter: float = typer.Option(help="Cellpose diameter parameter"),
    channels: list[str] = typer.Option(
        help="Names of the channels used for Cellpose. If one channel, then provide just a nucleus channel. If two channels, this is the nucleus and then the cytoplasm channel"
    ),
    flow_threshold: float = typer.Option(2, help="Cellpose `flow_threshold` parameter"),
    cellprob_threshold: float = typer.Option(-6, help="Cellpose `cellprob_threshold` parameter"),
    model_type: str = typer.Option("cyto2", help="Name of the cellpose model"),
    min_area: int = typer.Option(
        0, help="Minimum area (in pixels^2) for a cell to be considered as valid"
    ),
    clip_limit: float = typer.Option(
        0.2,
        help="Parameter for skimage.exposure.equalize_adapthist (applied before running cellpose)",
    ),
    gaussian_sigma: float = typer.Option(
        1, help="Parameter for scipy gaussian_filter (applied before running cellpose)"
    ),
    patch_index: int = typer.Option(
        default=None,
        help="Index of the patch on which cellpose should be run. NB: the number of patches is `len(sdata['sopa_patches'])`",
    ),
    patch_dir: str = typer.Option(
        default=None,
        help="Path to the temporary cellpose directory inside which we will store each individual patch segmentation. By default, saves into the `.sopa_cache/cellpose_boundaries` directory",
    ),
    patch_width: int = typer.Option(
        default=None, help="Ignore this if you already run `sopa patchify`. Patch width in pixels"
    ),
    patch_overlap: int = typer.Option(
        default=None,
        help="Ignore this if you already run `sopa patchify`. Patches overlaps in pixels",
    ),
):
    """Perform cellpose segmentation. This can be done on all patches directly, or on one individual patch.

    Usage:

        - [On one patch] Use this mode to run patches in parallel. Just provide `--patch-index` and `--patch-dir`. Note that `--patch-dir` will be used during `sopa resolve cellpose` afterwards.

        - [On all patches at once] For small images, you can run cellpose sequentially (no need to run `sopa patchify`). You need to provide `--patch-width` and `--patch-overlap`
    """
    from sopa._constants import SopaKeys
    from sopa.segmentation.methods import cellpose_patch

    method = cellpose_patch(
        diameter,
        channels,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
        model_type=model_type,
    )

    _run_staining_segmentation(
        sdata_path,
        SopaKeys.CELLPOSE_BOUNDARIES,
        method,
        channels,
        min_area,
        clip_limit,
        gaussian_sigma,
        patch_index,
        patch_dir,
        patch_width,
        patch_overlap,
    )


@app_segmentation.command()
def generic_staining(
    sdata_path: str = typer.Argument(help=SDATA_HELPER),
    method_name: str = typer.Option(
        help="Name of the segmentation method builder to use. The corresponding function (`sopa.segmentation.methods.<method_name>`) will be used, and the kwargs below will be used to instantiate the method."
    ),
    method_kwargs: str = typer.Option(
        {},
        callback=ast.literal_eval,
        help="Kwargs for the method. This should be a dictionnary, in inline string format.",
    ),
    channels: list[str] = typer.Option(help="Names of the channels used for segmentation."),
    min_area: int = typer.Option(
        0, help="Minimum area (in pixels^2) for a cell to be considered as valid"
    ),
    clip_limit: float = typer.Option(
        0.2,
        help="Parameter for skimage.exposure.equalize_adapthist (applied before running the segmentation method)",
    ),
    gaussian_sigma: float = typer.Option(
        1,
        help="Parameter for scipy gaussian_filter (applied before running the segmentation method)",
    ),
    patch_index: int = typer.Option(
        default=None,
        help="Index of the patch on which the segmentation method should be run. NB: the number of patches is `len(sdata['sopa_patches'])`",
    ),
    patch_dir: str = typer.Option(
        default=None,
        help="Path to the temporary the segmentation method directory inside which we will store each individual patch segmentation. By default, saves into the `.sopa_cache/<method_name>` directory",
    ),
    patch_width: int = typer.Option(
        default=None, help="Ignore this if you already run `sopa patchify`. Patch width in pixels"
    ),
    patch_overlap: int = typer.Option(
        default=None,
        help="Ignore this if you already run `sopa patchify`. Patches overlaps in pixels",
    ),
):
    """Perform generic staining-based segmentation. This can be done on all patches directly, or on one individual patch.

    Usage:
        First, define a new segmentation method, and write it under `sopa.segmentation.methods`. It should correspond to a function that is a "callable builder", i.e. kwargs will be provided to this function, and it will return a callable that will be applied on patches.

        As for Cellpose, two modes ara available:

        - [On one patch] Use this mode to run patches in parallel. Just provide `--patch-index` and `--patch-dir`. Note that `--patch-dir` will be used during `sopa resolve cellpose` afterwards.

        - [On all patches at once] For small images, you can run the segmentation method sequentially (no need to run `sopa patchify`). You need to provide `--patch-width` and `--patch-overlap`
    """
    from sopa.segmentation import methods

    assert hasattr(
        methods, method_name
    ), f"'{method_name}' is not a valid method builder under `sopa.segmentation.methods`"

    method = getattr(methods, method_name)(**method_kwargs)

    _run_staining_segmentation(
        sdata_path,
        method_name,
        method,
        channels,
        min_area,
        clip_limit,
        gaussian_sigma,
        patch_index,
        patch_dir,
        patch_width,
        patch_overlap,
    )


def _run_staining_segmentation(
    sdata_path: str,
    shapes_key: str,
    method,
    channels: list[str],
    min_area: float,
    clip_limit: float,
    gaussian_sigma: float,
    patch_index: int,
    patch_dir: str,
    patch_width: int,
    patch_overlap: int,
):
    from sopa.io.standardize import read_zarr_standardized
    from sopa.segmentation.stainings import StainingSegmentation

    from .utils import _default_boundary_dir

    sdata = read_zarr_standardized(sdata_path)

    segmentation = StainingSegmentation(
        sdata,
        method,
        channels,
        min_area=min_area,
        clip_limit=clip_limit,
        gaussian_sigma=gaussian_sigma,
    )

    if patch_index is not None:
        if patch_dir is None:
            patch_dir = _default_boundary_dir(sdata_path, shapes_key)

        segmentation.write_patch_cells(patch_dir, patch_index)
        return

    cells = segmentation.run_patches(patch_width, patch_overlap)

    StainingSegmentation.add_shapes(sdata, cells, segmentation.image_key, shapes_key)
