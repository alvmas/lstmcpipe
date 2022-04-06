#!/usr/bin/env python

from ruamel.yaml import YAML
import calendar
import logging

log = logging.getLogger(__name__)


def load_config(config_path):
    """
    Load the pipeline config, test for invalid values and
    set paths to the data files/directories.

    Parameters:
    -----------
    config_path: str or Path-like object
        Path to the config file

    Returns:
    --------
    config: dict
        Dictionary with parameters for the r0_to_dl3 processing
    """

    # This could easily be adapted to support different formats
    with open(config_path) as f:
        loaded_config = YAML().load(f)

    config_valid(loaded_config)

    config = complete_lstmcpipe_config(loaded_config)

    log.info(
        f'************ - lstMCpipe will be launch using the {config["workflow_kind"]} pipeline:- ************'
    )
    log.info(f'\nPROD_ID to be used: {config["prod_id"]}')
    log.info("\nStages to be run:\n - " + "\n - ".join(config["stages_to_run"]))

    if "merge_dl1" in config["stages_to_run"]:
        log.info("Merging options:" f"\n - No-image argument: {config['merge_dl1']['merging_no_image']}")

    if "r0_to_dl1" in config["stages_to_run"]:
        log.info(
            "Simtel DL0 files will be get from:" + "\n - ".join([i["input"] for i in config["r0_to_dl1"]])
        )
    elif "dl1ab" in config["stages_to_run"]:
        log.info(f'\nApplying dl1ab processing to MC prod: {config["dl1_reference_id"]}')
        log.info(
            "\nDL1 .h5 files will be get from:" + "\n - ".join([i["input"] for i in config["dl1ab"]])
        )
    else:
        pass

    log.info(
        "Slurm configuration:"
        + f"\n - Source environment: {config['batch_config']['source_environment']}"
        + f"\n - Slurm account: {config['batch_config']['slurm_account']}"
    )

    log.warning(
        "\n! Subdirectories with the same PROD_ID and analysed the same day will be overwritten !"
    )

    return config


def config_valid(loaded_config):
    """
    Test if the given dictionary contains valid values for the
    r0_to_dl3 processing.
    TODO: The stages should be checked aswell.
    Not all combinations are sensible!

    Parameters:
    -----------
    loaded_config: dict
        Dictionary with the values in the config file

    Returns:
    --------
    True if config is valid
    """
    # Allowed options
    compulsory_entries = [
        "workflow_kind",
        "prod_type",
        "source_environment",
        "stages_to_run",
        "stages",
        # TODO dl1_reference_id ?
    ]
    allowed_workflows = ["hiperta", "lstchain", "ctapipe"]
    allowed_prods = [
        "PathConfigProd5",
        "PathConfigProd5Trans80",
        "PathConfigProd5Trans80Dl1ab",
        "PathConfigAllSky",
    ]

    # Check allowed cases
    for item in compulsory_entries:
        if item not in loaded_config:
            raise Exception(
                f"The lstMCpipe configuration was not generated correctly. \n"
                f"Missing: {item} key"
            )

    workflow_kind = loaded_config["workflow_kind"]
    if workflow_kind not in allowed_workflows:
        raise Exception(
            f"Please select an allowed `workflow_kind`: {allowed_workflows}"
        )

    prod_type = loaded_config["prod_type"]
    if prod_type not in allowed_prods:
        raise Exception(f"Please selected an allowed production type: {allowed_prods}.")

    stages_to_be_run = loaded_config["stages_to_run"]
    if "dl1ab" in stages_to_be_run:
        if not "dl1_reference_id" in loaded_config:
            raise KeyError(
                "The key dl1_reference_id has to be set in order to locate "
                "the input files for the dl1ab stage"
            )

    dl1_noise_tune_data_run = loaded_config.get("dl1_noise_tune_data_run")
    dl1_noise_tune_mc_run = loaded_config.get("dl1_noise_tune_mc_run")
    if dl1_noise_tune_data_run and not dl1_noise_tune_mc_run:
        raise KeyError(
            "Please specify a simtel monte carlo file to "
            "compare observed noise against."
        )
    elif not dl1_noise_tune_data_run and dl1_noise_tune_mc_run:
        raise KeyError("Please specify an observed dl1 file to " "tune the images.")

    log.debug("Configuration deemed valid")

    return True


def complete_lstmcpipe_config(loaded_config):
    """
    Completes (and get default values) of some entries of the lstmcpipe config

    Parameters
    ----------
    loaded_config: dict
        Loaded config generated by lstmcpipe PathConfig

    Returns
    -------
    config : dict
        Dictionary with all the key:values completed along the r0_to_dl3 workflow

    """
    config = loaded_config.copy()

    sufix_prod_id = loaded_config.get("prod_id", "v00")
    workflow_kind = loaded_config["workflow_kind"]
    prod_type = loaded_config["prod_type"]

    # TODO ??
    # # to locate the source dl1 files
    # dl1_reference_id = loaded_config.get("dl1_reference_id")
    # # Full path to an observed dl1 file
    # dl1_noise_tune_data_run = loaded_config.get("dl1_noise_tune_data_run")
    # dl1_noise_tune_mc_run = loaded_config.get("dl1_noise_tune_mc_run")

    # Prod_id syntax
    t = calendar.datetime.date.today()
    year, month, day = f"{t.year:04d}", f"{t.month:02d}", f"{t.day:02d}"
    if workflow_kind == "lstchain":

        import lstchain
        base_prod_id = f"{year}{month}{day}_v{lstchain.__version__}"

    elif workflow_kind == "ctapipe":

        import ctapipe
        base_prod_id = f"{year}{month}{day}_vctapipe{ctapipe.__version__}"

    elif workflow_kind == "hiperta":  # RTA

        # TODO parse version from hiPeRTA module
        import lstchain
        base_prod_id = f"{year}{month}{day}_vRTA420_v{lstchain.__version__}"

    # Create the final config structure to be passed to the pipeline
    # 1 - Prod_id

    all_mc_prods = {
        "PathConfigProd5": "prod5",
        "PathConfigProd5Trans80": "prod5_trans_80",
        "PathConfigProd5Trans80Dl1ab": "prod5_trans_80",
        "PathConfigAllSky": "prod_all_sky",
    }

    suffix_id = "_{}_{}".format(all_mc_prods[prod_type], sufix_prod_id)
    config["prod_id"] = base_prod_id + suffix_id

    # 2 - Parse source environment correctly
    src_env = (
        f"source {loaded_config['source_environment']['source_file']}; "
        f"conda activate {loaded_config['source_environment']['conda_env']}; "
    )
    # 2.1 - Parse slurm user config account
    slurm_account = loaded_config.get("slurm_config", {}).get("user_account", "")

    # 2.2 - Create a dict for all env configuration and slurm configuration (batch arguments)
    config["batch_config"] = {
        "source_environment": src_env,
        "slurm_account": slurm_account,
    }

    # TODO ??
    # config["dl1_reference_id"] = dl1_reference_id
    # config["dl1_noise_tune_data_run"] = dl1_noise_tune_data_run
    # config["dl1_noise_tune_mc_run"] = dl1_noise_tune_mc_run

    return config
