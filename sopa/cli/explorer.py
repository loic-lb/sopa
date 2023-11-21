import typer

from .utils import SDATA_HELPER

app_explorer = typer.Typer()


@app_explorer.command()
def write(
    sdata_path: str = typer.Argument(help=SDATA_HELPER),
    output_path: str = typer.Option(
        None,
        help="Path to a directory where Xenium Explorer's outputs will be saved. By default, writes to the same path as `sdata_path` but with the `.explorer` suffix",
    ),
    gene_column: str = typer.Option(
        None, help="Column name of the points dataframe containing the gene names"
    ),
    shapes_key: str = typer.Option(
        None,
        help="Key for the boundaries. By default, uses the baysor boundaires, else the cellpose boundaries",
    ),
    lazy: bool = typer.Option(
        True,
        help="If `True`, will not load the full images in memory (except if the image memory is below `ram_threshold_gb`)",
    ),
    ram_threshold_gb: int = typer.Option(
        4,
        help="Threshold (in gygabytes) from which image can be loaded in memory. If `None`, the image is never loaded in memory",
    ),
    mode: str = typer.Option(
        None,
        help="string that indicated which files should be created. `'-ib'` means everything except images and boundaries, while `'+tocm'` means only transcripts/observations/counts/metadata (each letter corresponds to one explorer file). By default, keeps everything",
    ),
):
    """Convert a spatialdata object to Xenium Explorer's inputs"""
    from pathlib import Path

    from sopa.io.explorer import write_explorer
    from sopa.io.standardize import read_zarr_standardized

    sdata = read_zarr_standardized(sdata_path)

    if output_path is None:
        output_path = Path(sdata_path).with_suffix(".explorer")

    write_explorer(
        output_path,
        sdata,
        shapes_key=shapes_key,
        gene_column=gene_column,
        lazy=lazy,
        ram_threshold_gb=ram_threshold_gb,
        mode=mode,
    )


@app_explorer.command()
def add_aligned(
    sdata_path: str = typer.Argument(help=SDATA_HELPER),
    image_path: str = typer.Argument(
        help="Path to the image file to be added (`.ome.tif` used in the explorer during alignment)"
    ),
    transformation_matrix_path: str = typer.Argument(
        help="Path to the `matrix.csv` file returned by the Explorer after alignment"
    ),
):
    """After alignment on the Xenium Explorer, add an image to the SpatialData object"""
    import spatialdata

    from sopa import io
    from sopa.io.explorer.images import align

    sdata = spatialdata.read_zarr(sdata_path)
    image = io.imaging.xenium_if(image_path)

    align(sdata, image, transformation_matrix_path)