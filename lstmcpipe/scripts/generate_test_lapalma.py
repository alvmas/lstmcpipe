"""
Script to generate a mini production tree with symlinks to a few simtel files and the corresponding path config.
This is used to test lstmcpipe on a small prod
"""

from pathlib import Path
from tqdm import tqdm
from datetime import date
import os
import argparse

from lstmcpipe.config import paths_config


def generate_tree(base_dir, working_dir, nfiles):
    """
    Walk the base dir looking for simtels files
    When a directory contains simtels files, it's tree structure is duplicated into the working dir
    and nfiles are symlinked there
    """
    base_dir = Path(base_dir)
    working_dir = Path(working_dir)

    for root, dirs, files in tqdm(os.walk(base_dir)):
        simtel_files = [os.path.join(root, file) for file in files if file.endswith('.simtel.gz')]
        if simtel_files:
            for file in simtel_files[:nfiles]:
                target = working_dir.joinpath(Path(file).relative_to(base_dir))
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.symlink_to(file)


def generate_test_prod5trans80(
    working_dir='/fefs/aswg/workspace/lstmcpipe/data/mc/',
    nfiles=5, 
    path_to_config_file=f'test_prod5trans80_{date.today()}.yaml',
    overwrite=True
):
    base_dir = '/fefs/aswg/workspace/lstmcpipe/data/test_data/mc/DL0/20200629_prod5_trans_80/'
    working_dir = os.path.join(working_dir, 'DL0/20200629_prod5_trans_80/')

    generate_tree(base_dir, working_dir, nfiles)

    pc = paths_config.PathConfigProd5Trans80(f'test_prod_{date.today()}')
    pc.base_dir = os.path.join(
        working_dir, '{data_level}/20200629_prod5_trans_80/{particle}/{zenith}/south_pointing/{prod_id}'
    )
    pc.generate()
    pc.save_yml(path_to_config_file, overwrite=overwrite)


def generate_test_allsky(
    working_dir='/fefs/aswg/workspace/lstmcpipe/data/mc/',
    nfiles=5,
    path_to_config_file=f'test_AllSky_{date.today()}.yaml',
    decs=['dec_4822', 'dec_931'],
    overwrite=True,
):
    """
    returns 
    """
    allsky_train_base_dir = '/home/georgios.voutsinas/ws/AllSky'
    allsky_test_base_dir = '/home/georgios.voutsinas/ws/AllSky'

    generate_tree(allsky_train_base_dir, os.path.join(working_dir, 'DL0/AllSky'), nfiles)

    pc = paths_config.PathConfigAllSkyFull(f'test_prod_{date.today()}', decs)
    # config training dir are replaced with local ones
    for dec in decs:
        pc.train_configs[dec].base_dir = os.path.join(
            working_dir, '{data_level}/AllSky/{prod_id}/{dataset_type}/{dec}/{particle}/{pointing}/'
        )
        pc.test_configs[dec].base_dir = os.path.join(
            working_dir, '{data_level}/AllSky/{prod_id}/{dataset_type}/{dec}/{particle}/{pointing}/'
        )
        pc.train_configs[dec].training_dir = os.path.join(
            working_dir, pc.train_configs[dec].training_dir.replace(allsky_train_base_dir, 'DL0/AllSky/')
        )
        pc.test_configs[dec].testing_dir = os.path.join(
            working_dir, pc.test_configs[dec].testing_dir.replace(allsky_test_base_dir, 'DL0/AllSky/')
        )
    pc.generate()
    pc.save_yml(path_to_config_file, overwrite=overwrite)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate test tree')

    parser.add_argument('prod_type', type=str, help='prod5trans80 or allsky')
    parser.add_argument('--nfiles', type=int, default=5, help='Number of files')
    parser.add_argument('--config_file_dir', type=Path, default='.', help='Path to save the corresponding config files')
    parser.add_argument(
        '--working_dir',
        type=Path,
        default='/fefs/aswg/workspace/lstmcpipe/data/mc/',
        help='Your working dir where the DL0 tree will be generated, '
        '(such as /fefs/aswg/workspace/firstname.surname/data/mc/)',
    )

    args = parser.parse_args()

    if args.prod_type == 'prod5trans80':
        config_file_path = Path(args.path_config_file, f'test_prod5trans80_{date.today()}.yaml')
        generate_test_prod5trans80(args.working_dir, args.nfiles, config_file_path)
    elif args.prod_type == 'allsky':
        config_file_path = Path(args.path_config_file, f'test_AllSky_{date.today()}.yaml')
        generate_test_allsky(args.working_dir, args.nfiles, config_file_path)
    else:
        raise NotImplementedError("Unknown prod type")
