# -*- coding: utf-8 -*-
"""
NewPayloadUpdatedWizard_v140_Enhanced.py

Adds:
- Test Connection button on Credentials page
- CSV audit in chosen output folder (payload_wizard_audit.csv)
- Keeps JSONL audit in ./logs/query_audit.jsonl
- One-click Run Export → Launch Viewer
- SELECT-only, read-only session, timeouts, and early disconnect
"""

import os
import re
import sys
import csv
import json
import time
import tempfile
import threading
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_VERSION = "1.4.0-wizard-enhanced"
HERE = Path(__file__).resolve().parent

# Connection and timeout constants
STATEMENT_TIMEOUT_MS = 120000  # 2 minutes
IDLE_SESSION_TIMEOUT_MS = 60000  # 1 minute
CONNECTION_TIMEOUT_SEC = 8
CONNECT_RETRY_DELAYS = [0, 3, 6, 10]  # seconds
MAX_QUERY_LOG_LENGTH = 2000  # characters

# Audit folder configuration
AUDIT_FOLDER_NAME = "audit_logs"  # Separate folder for audit CSVs

# ------------------------ Presets ------------------------
HOSTMAP = {
    ("SA-Central", "MTF"):  {"hosts": ["ljnb5cdb7466","lgg5cdb7083","lqra5cdb7600"], "port":6432, "dbname":"pgdb_msdc1", "schema":"sdc_owner"},
    ("SA-Central", "PROD"): {"hosts": ["ljnb5cdb753","lqra5cdb8013","lqra5cdb7706"], "port":6432, "dbname":"pgdb_padc1", "schema":"sdc_owner"},
    ("US Central", "MTF"):  {"hosts": ["lkc2cdb7525","lmk2cdb7489","lkc2cdb7686"],   "port":6432, "dbname":"pgdb_pawd001","schema":"sdc_owner"},
    ("US Central", "PROD"): {"hosts": ["lkc2cdb7525","lmk2cdb7489","lkc2cdb7686"],   "port":6432, "dbname":"pgdb_pawd001","schema":"sdc_owner"},
    ("MTF Global","MTF"):   {"hosts": ["lstl5cdb7301","lstl5cdb7357","lstl5cdb7188"], "port":6432, "dbname":"pgdb_msdc001","schema":"sdc_owner"},
    ("MTF Global","PROD"):  {"hosts": ["lstl5cdb7301","lstl5cdb7357","lstl5cdb7188"], "port":6432, "dbname":"pgdb_msdc001","schema":"sdc_owner"},
    ("SDC-STL Global","MTF"):{"hosts":["lstl2cdb5798","lstl2cdb4369","lstl2cdb5380"], "port":6432, "dbname":"pgdb_pawd002","schema":"swd_owner"},
    ("SDC-STL Global","PROD"):{"hosts":["lstl2cdb5798","lstl2cdb4369","lstl2cdb5380"],"port":6432, "dbname":"pgdb_pawd002","schema":"swd_owner"},
    ("SDC-KSC Global","MTF"): {"hosts":["lkc2cdb5172","lkc2cdb5163","lkc2cdb5284"],   "port":6432, "dbname":"pgdb_pawd003","schema":"swd_owner"},
    ("SDC-KSC Global","PROD"):{"hosts":["lkc2cdb5172","lkc2cdb5163","lkc2cdb5284"],   "port":6432, "dbname":"pgdb_pawd003","schema":"swd_owner"},
}
REGIONS = sorted({r for r,_ in HOSTMAP.keys()})
ENVS    = sorted({e for _,e in HOSTMAP.keys()})

DEFAULT_SQL = """\
select 'issr_profl' as "Config Name", A.issr_profl_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.issr_profl A
LEFT JOIN sdc_owner.issr_profl B ON 
  A.issr_profl_upstream_id = B.issr_profl_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'acc_rng_sch_cca' as "Config Name", A.acc_rng_sch_cca_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.acc_rng_sch_cca A
LEFT JOIN sdc_owner.acc_rng_sch_cca B ON
  A.acc_rng_sch_cca_upstream_id = B.acc_rng_sch_cca_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'acc_rng_sch_sepa_cca' as "Config Name", A.acc_rng_sch_sp_cca_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.acc_rng_sch_sepa_cca A
LEFT JOIN sdc_owner.acc_rng_sch_sepa_cca B ON
  A.acc_rng_sch_sp_cca_upstream_id = B.acc_rng_sch_sp_cca_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'acq_profl' as "Config Name", A.acq_profl_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.acq_profl A
LEFT JOIN sdc_owner.acq_profl B ON
  A.acq_profl_upstream_id = B.acq_profl_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'acq_ref_b2b_agrmt' as "Config Name", A.acq_ref_b2b_agrmt_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.acq_ref_b2b_agrmt A
LEFT JOIN sdc_owner.acq_ref_b2b_agrmt B ON
  A.acq_ref_b2b_agrmt_upstream_id = B.acq_ref_b2b_agrmt_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'acq_ref_id' as "Config Name", A.acq_ref_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.acq_ref_id A
LEFT JOIN sdc_owner.acq_ref_id B ON
  A.acq_ref_upstream_id = B.acq_ref_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'b2b_agrmt' as "Config Name", A.b2b_agrmt_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.b2b_agrmt A
LEFT JOIN sdc_owner.b2b_agrmt B ON
  A.b2b_agrmt_upstream_id = B.b2b_agrmt_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'brnd_prdct' as "Config Name", A.brnd_prdct_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.brnd_prdct A
LEFT JOIN sdc_owner.brnd_prdct B ON
  A.brnd_prdct_upstream_id = B.brnd_prdct_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'bsa_config' as "Config Name", A.bsa_config_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.bsa_config A
LEFT JOIN sdc_owner.bsa_config B ON
  A.bsa_config_upstream_id = B.bsa_config_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'busn_cycle' as "Config Name", A.busn_cycle_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.busn_cycle A
LEFT JOIN sdc_owner.busn_cycle B ON
  A.busn_cycle_upstream_id = B.busn_cycle_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'canonical_fld_cnstrnt' as "Config Name", A.canonical_fld_cnstrnt_upstream as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.canonical_fld_cnstrnt A
LEFT JOIN sdc_owner.canonical_fld_cnstrnt B ON
  A.canonical_fld_cnstrnt_upstream = B.canonical_fld_cnstrnt_upstream AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cbfm_override' as "Config Name", A.cbfm_override_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cbfm_override A
LEFT JOIN sdc_owner.cbfm_override B ON
  A.cbfm_override_upstream_id = B.cbfm_override_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cca_exclsn' as "Config Name", A.cca_exclsn_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cca_exclsn A
LEFT JOIN sdc_owner.cca_exclsn B ON
  A.cca_exclsn_upstream_id = B.cca_exclsn_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'chgbk_prtct_limit' as "Config Name", A.chgbk_prtct_limit_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.chgbk_prtct_limit A
LEFT JOIN sdc_owner.chgbk_prtct_limit B ON
  A.chgbk_prtct_limit_upstream_id = B.chgbk_prtct_limit_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'clr_issr_cca' as "Config Name", A.clr_issr_cca_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.clr_issr_cca A
LEFT JOIN sdc_owner.clr_issr_cca B ON
  A.clr_issr_cca_upstream_id = B.clr_issr_cca_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'clr_mbr' as "Config Name", A.clr_mbr_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.clr_mbr A
LEFT JOIN sdc_owner.clr_mbr B ON
  A.clr_mbr_upstream_id = B.clr_mbr_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'clr_prcssr_config' as "Config Name", A.clr_prcssr_config_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.clr_prcssr_config A
LEFT JOIN sdc_owner.clr_prcssr_config B ON
  A.clr_prcssr_config_upstream_id = B.clr_prcssr_config_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cncl_xpath_def' as "Config Name", A.cncl_xpath_def_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cncl_xpath_def A
LEFT JOIN sdc_owner.cncl_xpath_def B ON
  A.cncl_xpath_def_upstream_id = B.cncl_xpath_def_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cntry' as "Config Name", A.cntry_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cntry A
LEFT JOIN sdc_owner.cntry B ON
  A.cntry_upstream_id = B.cntry_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cntry_cca' as "Config Name", A.cntry_cca_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cntry_cca A
LEFT JOIN sdc_owner.cntry_cca B ON
  A.cntry_cca_upstream_id = B.cntry_cca_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cross_brdr_fee' as "Config Name", A.cross_brdr_fee_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cross_brdr_fee A
LEFT JOIN sdc_owner.cross_brdr_fee B ON
  A.cross_brdr_fee_upstream_id = B.cross_brdr_fee_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'crtr' as "Config Name", A.crtr_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.crtr A
LEFT JOIN sdc_owner.crtr B ON
  A.crtr_upstream_id = B.crtr_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'curr' as "Config Name", A.curr_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.curr A
LEFT JOIN sdc_owner.curr B ON
  A.curr_upstream_id = B.curr_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'curr_conv_dec' as "Config Name", A.curr_conv_dec_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.curr_conv_dec A
LEFT JOIN sdc_owner.curr_conv_dec B ON
  A.curr_conv_dec_upstream_id = B.curr_conv_dec_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cust_blck_cfg' as "Config Name", A.cust_blck_cfg_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cust_blck_cfg A
LEFT JOIN sdc_owner.cust_blck_cfg B ON
  A.cust_blck_cfg_upstream_id = B.cust_blck_cfg_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cust_rpt_dist' as "Config Name", A.cust_rpt_dist_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cust_rpt_dist A
LEFT JOIN sdc_owner.cust_rpt_dist B ON
  A.cust_rpt_dist_upstream_id = B.cust_rpt_dist_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'cvm_limit' as "Config Name", A.cvm_limit_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.cvm_limit A
LEFT JOIN sdc_owner.cvm_limit B ON
  A.cvm_limit_upstream_id = B.cvm_limit_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'echo_rule' as "Config Name", A.echo_rule_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.echo_rule A
LEFT JOIN sdc_owner.echo_rule B ON
  A.echo_rule_upstream_id = B.echo_rule_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'ecn_exchng_pgm' as "Config Name", A.ecn_exchng_pgm_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.ecn_exchng_pgm A
LEFT JOIN sdc_owner.ecn_exchng_pgm B ON
  A.ecn_exchng_pgm_upstream_id = B.ecn_exchng_pgm_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'ecn_exchng_rates' as "Config Name", A.ecn_exchng_rates_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.ecn_exchng_rates A
LEFT JOIN sdc_owner.ecn_exchng_rates B ON
  A.ecn_exchng_rates_upstream_id = B.ecn_exchng_rates_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'ecn_exchng_tier' as "Config Name", A.ecn_exchng_tier_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.ecn_exchng_tier A
LEFT JOIN sdc_owner.ecn_exchng_tier B ON
  A.ecn_exchng_tier_upstream_id = B.ecn_exchng_tier_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'eco_fee_valdtn' as "Config Name", A.eco_fee_valdtn_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.eco_fee_valdtn A
LEFT JOIN sdc_owner.eco_fee_valdtn B ON
  A.eco_fee_valdtn_upstream_id = B.eco_fee_valdtn_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'economics' as "Config Name", A.economics_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.economics A
LEFT JOIN sdc_owner.economics B ON
  A.economics_upstream_id = B.economics_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'economics_canonical_data' as "Config Name", A.ecnmcs_canncl_data_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.economics_canonical_data A
LEFT JOIN sdc_owner.economics_canonical_data B ON
  A.ecnmcs_canncl_data_upstream_id = B.ecnmcs_canncl_data_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL 
select 'economics_vldtn' as "Config Name", A.ecnmcs_val_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.economics_vldtn A
LEFT JOIN sdc_owner.economics_vldtn B ON
  A.ecnmcs_val_upstream_id = B.ecnmcs_val_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'endpnt_file_frmt' as "Config Name", A.endpnt_file_frmt_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts 
FROM sdc_owner.endpnt_file_frmt A
LEFT JOIN sdc_owner.endpnt_file_frmt B ON
  A.endpnt_file_frmt_upstream_id = B.endpnt_file_frmt_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'err_desc_data' as "Config Name", A.err_desc_data_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.err_desc_data A
LEFT JOIN sdc_owner.err_desc_data B ON
  A.err_desc_data_upstream_id = B.err_desc_data_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'flag_data' as "Config Name", A.flag_data_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.flag_data A
LEFT JOIN sdc_owner.flag_data B ON
  A.flag_data_upstream_id = B.flag_data_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'historical_curr_rate' as "Config Name", A.historical_curr_rate_upstrm_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.historical_curr_rate A
LEFT JOIN sdc_owner.historical_curr_rate B ON
  A.historical_curr_rate_upstrm_id = B.historical_curr_rate_upstrm_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'instl_cfg' as "Config Name", A.instl_cfg_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.instl_cfg A
LEFT JOIN sdc_owner.instl_cfg B ON
  A.instl_cfg_upstream_id = B.instl_cfg_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'intr_int_reg_cca' as "Config Name", A.intr_int_reg_cca_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.intr_int_reg_cca A
LEFT JOIN sdc_owner.intr_int_reg_cca B ON
  A.intr_int_reg_cca_upstream_id = B.intr_int_reg_cca_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'intr_mem_iden' as "Config Name", A.intr_mem_iden_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.intr_mem_iden A
LEFT JOIN sdc_owner.intr_mem_iden B ON
  A.intr_mem_iden_upstream_id = B.intr_mem_iden_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'issr_crdntl_rng_b2b_agrmt' as "Config Name", A.issr_crdntl_agrmt_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.issr_crdntl_rng_b2b_agrmt A
LEFT JOIN sdc_owner.issr_crdntl_rng_b2b_agrmt B ON
  A.issr_crdntl_agrmt_upstream_id = B.issr_crdntl_agrmt_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'issr_profl_glb' as "Config Name", A.issr_profl_glb_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.issr_profl_glb A
LEFT JOIN sdc_owner.issr_profl_glb B ON
  A.issr_profl_glb_upstream_id = B.issr_profl_glb_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'mc_asned' as "Config Name", A.mc_asned_id_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.mc_asned A
LEFT JOIN sdc_owner.mc_asned B ON
  A.mc_asned_id_upstream_id = B.mc_asned_id_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'mc_rate' as "Config Name", A.mc_rate_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.mc_rate A
LEFT JOIN sdc_owner.mc_rate B ON
  A.mc_rate_upstream_id = B.mc_rate_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'mcc_pgm_cd' as "Config Name", A.mcc_pgm_cd_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.mcc_pgm_cd A
LEFT JOIN sdc_owner.mcc_pgm_cd B ON
  A.mcc_pgm_cd_upstream_id = B.mcc_pgm_cd_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'mcc_prgm_geo' as "Config Name", A.mcc_prgm_geo_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.mcc_prgm_geo A
LEFT JOIN sdc_owner.mcc_prgm_geo B ON
  A.mcc_prgm_geo_upstream_id = B.mcc_prgm_geo_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'mdes_fpan_acct_rng' as "Config Name", A.mdes_fpan_acct_rng_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.mdes_fpan_acct_rng A
LEFT JOIN sdc_owner.mdes_fpan_acct_rng B ON
  A.mdes_fpan_acct_rng_upstream_id = B.mdes_fpan_acct_rng_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours')
UNION ALL
select 'money_send' as "Config Name", A.money_send_upstream_id as "Config Key", A.pyld as "CURRENT PAYLOAD", B.pyld as "OLD PAYLOAD", A.config_eff_ts, A.rec_sts, A.param_exp_ts
FROM sdc_owner.money_send A
LEFT JOIN sdc_owner.money_send B ON
  A.money_send_upstream_id = B.money_send_upstream_id AND
  A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW()- INTERVAL '24 hours'])

"""

# ------------------------ Deps ------------------------
try:
    import pandas as pd
except Exception as e:
    raise SystemExit("pandas is required (pip install pandas openpyxl).") from e

HAVE_PG3 = False
HAVE_PG2 = False
psycopg3 = None
psycopg2 = None
try:
    import psycopg as psycopg3  # v3
    HAVE_PG3 = True
except Exception:
    pass
if not HAVE_PG3:
    try:
        import psycopg2  # v2
        HAVE_PG2 = True
    except Exception:
        pass
if not (HAVE_PG3 or HAVE_PG2):
    raise SystemExit("Install a Postgres driver: pip install psycopg[binary]  (or)  pip install psycopg2")

# ------------------------ Logging & Audit ------------------------
def _ensure_log_dir(base: Path) -> Path:
    try:
        base.mkdir(parents=True, exist_ok=True)
        t = base / ".write_test"
        t.write_text("ok", encoding="utf-8")
        t.unlink(missing_ok=True)
        return base
    except Exception:
        home = Path.home() / "payload_wizard_logs"
        home.mkdir(parents=True, exist_ok=True)
        return home

LOG_DIR = _ensure_log_dir(HERE / "logs")
APP_LOG = LOG_DIR / "app.log"
AUDIT_JSONL = LOG_DIR / "query_audit.jsonl"
AUDIT_CSV_BASENAME = "payload_wizard_audit.csv"  # this one goes in the selected output folder

logger = logging.getLogger("payload_wizard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = RotatingFileHandler(APP_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(h)

def audit_write_jsonl(obj: dict):
    try:
        with AUDIT_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        alt = Path.home() / "query_audit.jsonl"
        with alt.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        logger.warning("Audit JSONL fallback to %s due to %s", alt, e)

def audit_write_csv(outdir: str, row: dict) -> str:
    # Write audit CSV to a separate audit_logs subfolder
    try:
        out = Path(outdir) if outdir else Path.home()
        # Create audit_logs subfolder
        audit_dir = out / AUDIT_FOLDER_NAME
        audit_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        out = Path.home()
        audit_dir = out / AUDIT_FOLDER_NAME
        audit_dir.mkdir(parents=True, exist_ok=True)
    csv_path = audit_dir / AUDIT_CSV_BASENAME
    fieldnames = [
        "timestamp","op","status","error_message","duration_ms",
        "region","environment","host","port","db_name","schema",
        "user","driver","mode","row_count","export_csv","export_xlsx","query_sha256"
    ]
    exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return str(csv_path)

# ------------------------ SQL guards ------------------------
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|CREATE|GRANT|REVOKE|VACUUM|ANALYZE)\b", re.I)

def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    out = []
    for line in sql.splitlines():
        out.append(line.split("--", 1)[0])
    return "\n".join(out)

def sanitize_sql_for_log(sql: str, maxlen: int = MAX_QUERY_LOG_LENGTH) -> str:
    s = " ".join(sql.split())
    return (s[:maxlen] + " ...<truncated>") if len(s) > maxlen else s

def validate_select_only(sql: str) -> tuple[bool, str]:
    cleaned = strip_comments(sql).strip()
    if not cleaned:
        return False, "Query is empty."
    parts = [p for p in cleaned.split(";") if p.strip()]
    if len(parts) > 1:
        return False, "Only one statement is allowed."
    body = parts[0].lstrip()
    if not (body.lower().startswith("select") or body.lower().startswith("with")):
        return False, "Query must start with SELECT or WITH."
    if FORBIDDEN.search(body):
        return False, "Forbidden keyword detected. Only SELECT is allowed."
    return True, ""

def auto_fix_sql(sql: str, schema: str) -> tuple[str, list[str]]:
    notes = []
    original = sql
    if "{schema}" in sql:
        sql = sql.replace("{schema}", schema); notes.append(f"filled {{schema}} → {schema}")
    stripped = strip_comments(sql)
    parts = [p for p in stripped.split(";") if p.strip()]
    if len(parts) > 1:
        sql = parts[0].strip(); notes.append("removed extra statements after first semicolon")
    else:
        sql = parts[0].strip()
    if original.strip().endswith(";"):
        notes.append("removed trailing semicolon")
    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        m = re.search(r"\b(with|select)\b", low)
        if m:
            sql = sql[m.start():].strip(); notes.append("trimmed leading non-SELECT content")
    return sql, notes

# ------------------------ DB connect ------------------------
def connect_pg(host: str, port: int, dbname: str, user: str, pwd: str):
    options = f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c idle_in_transaction_session_timeout={IDLE_SESSION_TIMEOUT_MS}"
    last = None
    for wait in CONNECT_RETRY_DELAYS:
        if wait:
            time.sleep(wait)
        try:
            if HAVE_PG3:
                conn = psycopg3.connect(host=host, port=port, dbname=dbname, user=user, password=pwd,
                                        connect_timeout=CONNECTION_TIMEOUT_SEC, options=options)
            else:
                conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=pwd,
                                        connect_timeout=CONNECTION_TIMEOUT_SEC, options=options)
            cur = conn.cursor()
            try:
                cur.execute("SET application_name='payload_wizard'")
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            finally:
                try: cur.close()
                except Exception: pass
            return conn
        except Exception as e:
            last = e
            msg = str(e).lower()
            if "too many connections" in msg or "remaining connection slots" in msg:
                logging.warning("Pool full: %s", e)
                continue
            raise
    raise last

# ------------------------ Viewer launch ------------------------
CANDIDATES = [
    "GeminiPayloadDiff.py", "GeminiPayloadDiff_FIXED.py",
    "PayloadDiffViewer.exe", "GeminiPayloadDiff.exe",
    "payload_diff_viewer.py", "PayloadDiffViewer.py", "Test103.py"
]


def find_viewer() -> Path | None:
    env = os.environ.get("PAYLOADDIFF_VIEWER_PATH", "").strip()
    if env and Path(env).exists():
        return Path(env)
    for name in CANDIDATES:
        p = HERE / name
        if p.exists():
            return p
    return None

def launch_viewer(preferred_file: Path, logcb) -> bool:
    """Launch GeminiPayloadDiff viewer with the exported file."""
    viewer = find_viewer()
    if not viewer:
        logcb("❌ No GeminiPayloadDiff viewer found")
        messagebox.showwarning(
            "Viewer Not Found",
            "GeminiPayloadDiff.py not found in the same folder.\n\n"
            "Place GeminiPayloadDiff_FIXED.py or GeminiPayloadDiff.py next to this script\n"
            "or set PAYLOADDIFF_VIEWER_PATH environment variable."
        )
        return False

    logcb(f"✅ Found viewer: {viewer.name}")
    is_py = viewer.suffix.lower() == ".py"
    base = [sys.executable, str(viewer)] if is_py else [str(viewer)]

    # Try command-line argument formats (works with GeminiPayloadDiff_FIXED.py)
    variants = [
        base + ["--open", str(preferred_file)],
        base + ["-o", str(preferred_file)],
        base + ["--file", str(preferred_file)],
        base + ["-f", str(preferred_file)],
        base + [str(preferred_file)],
    ]

    for args in variants:
        try:
            subprocess.Popen(args)
            logcb(f"✅ Launched: {' '.join([os.path.basename(a) for a in args[:2]])} with {preferred_file.name}")
            return True
        except Exception as e:
            logcb(f"⚠️  Attempt failed: {e}")

    logcb("❌ All launch attempts failed")
    return False

# ------------------------ GUI ------------------------
class ParentScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        pad = {"padx": 10, "pady": 8}
        ttk.Label(self, text="REGION").grid(row=0, column=0, sticky="w", **pad)
        self.cb_region = ttk.Combobox(self, values=REGIONS, state="readonly"); self.cb_region.grid(row=0, column=1, sticky="we", **pad)
        ttk.Label(self, text="Environment").grid(row=0, column=2, sticky="w", **pad)
        self.cb_env = ttk.Combobox(self, values=ENVS, state="readonly"); self.cb_env.grid(row=0, column=3, sticky="we", **pad)
        ttk.Label(self, text="Utility / Run").grid(row=1, column=0, sticky="w", **pad)
        self.cb_util = ttk.Combobox(self, values=["Payload Comparison"], state="readonly", width=28); self.cb_util.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(self, text="Next →", command=self.on_next).grid(row=2, column=3, sticky="e", **pad)
        for c in range(4): self.columnconfigure(c, weight=1)

    def on_next(self):
        region = self.cb_region.get().strip()
        env = self.cb_env.get().strip()
        util = self.cb_util.get().strip()
        if not (region and env and util):
            messagebox.showerror("Choose all fields", "Select Region, Environment, and Utility"); return
        cfg = HOSTMAP.get((region, env))
        if not cfg:
            messagebox.showerror("No host mapping", "Add HOSTMAP entry in code"); return
        self.app.selection = {"region":region,"env":env,"util":util,"cfg":cfg}
        self.app.show_creds()

class CredsScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        pad = {"padx": 10, "pady": 8}

        self.var_host = tk.StringVar()
        self.var_port = tk.StringVar()
        self.var_db   = tk.StringVar()

        ttk.Label(self, text="Host").grid(row=0, column=0, sticky="w", **pad)
        self.cb_host = ttk.Combobox(self, textvariable=self.var_host, values=[], state="readonly", width=42)
        self.cb_host.grid(row=0, column=1, sticky="we", **pad)

        ttk.Label(self, text="Port").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.var_port, width=10).grid(row=0, column=3, sticky="w", **pad)

        ttk.Label(self, text="DB").grid(row=0, column=4, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.var_db, width=18).grid(row=0, column=5, sticky="w", **pad)

        ttk.Label(self, text="User").grid(row=1, column=0, sticky="w", **pad)
        self.e_user = ttk.Entry(self, width=26); self.e_user.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Password").grid(row=1, column=2, sticky="w", **pad)
        self.e_pwd = ttk.Entry(self, width=26, show="*"); self.e_pwd.grid(row=1, column=3, sticky="w", **pad)

        ttk.Label(self, text="Output folder").grid(row=1, column=4, sticky="w", **pad)
        self.e_out = ttk.Entry(self, width=28); self.e_out.insert(0, str(Path.home()))
        self.e_out.grid(row=1, column=5, sticky="we", **pad)
        ttk.Button(self, text="Browse", command=self.on_browse).grid(row=1, column=6, sticky="w", **pad)

        # NEW: Test Connection on creds form
        ttk.Button(self, text="Test Connection", command=self.on_test).grid(row=0, column=6, sticky="e", **pad)

        ttk.Button(self, text="← Back", command=self.app.show_parent).grid(row=2, column=0, sticky="w", **pad)
        ttk.Button(self, text="Next →", command=self.on_next).grid(row=2, column=6, sticky="e", **pad)

        for c in range(7): self.columnconfigure(c, weight=1)

    def on_browse(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.e_out.delete(0, tk.END); self.e_out.insert(0, d)

    def load_from_selection(self):
        cfg = self.app.selection["cfg"]; hosts = cfg.get("hosts")
        if hosts:
            self.cb_host["values"] = list(hosts); self.var_host.set(hosts[0])
        else:
            self.cb_host["values"] = [cfg.get("host","")]; self.var_host.set(cfg.get("host",""))
        self.var_port.set(str(cfg.get("port", 6432))); self.var_db.set(cfg.get("dbname","sdc"))

    def on_test(self):
        try:
            host = self.var_host.get().strip()
            port = int(self.var_port.get().strip())
            db   = self.var_db.get().strip()
            user = self.e_user.get().strip()
            pwd  = self.e_pwd.get().strip()
            outdir = self.e_out.get().strip()
            if not (host and port and db and user and pwd and outdir):
                messagebox.showerror("Inputs", "Fill all fields and choose output folder"); return
        except Exception:
            messagebox.showerror("Inputs", "Fill all fields and choose output folder"); return

        t0 = time.perf_counter()
        try:
            conn = connect_pg(host, port, db, user, pwd); conn.close()
            dt = int((time.perf_counter() - t0) * 1000)
            messagebox.showinfo("Connection OK", f"Connected in {dt} ms.")
            audit_write_jsonl({"ts_iso":datetime.now().isoformat(timespec="seconds"),
                               "op":"test_connection","status":"success",
                               "host":host,"port":port,"db_name":db})
            audit_write_csv(outdir, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "op": "test_connection", "status": "success", "error_message": "",
                "duration_ms": dt,
                "region": self.app.selection.get("region"),
                "environment": self.app.selection.get("env"),
                "host": host, "port": port, "db_name": db,
                "schema": self.app.selection.get("cfg",{}).get("schema",""),
                "user": user, "driver": "psycopg3" if HAVE_PG3 else "psycopg2",
                "mode": "", "row_count": 0, "export_csv": "", "export_xlsx": "", "query_sha256": ""
            })
            self.app._last_test_ok = True
            self.app._last_outdir = outdir
        except Exception as e:
            messagebox.showerror("Connection failed", str(e))
            audit_write_jsonl({"ts_iso":datetime.now().isoformat(timespec="seconds"),
                               "op":"test_connection","status":"error","error_message":str(e),
                               "host":host,"port":port,"db_name":db})
            audit_write_csv(outdir, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "op": "test_connection", "status": "error", "error_message": str(e),
                "duration_ms": 0,
                "region": self.app.selection.get("region"),
                "environment": self.app.selection.get("env"),
                "host": host, "port": port, "db_name": db,
                "schema": self.app.selection.get("cfg",{}).get("schema",""),
                "user": user, "driver": "psycopg3" if HAVE_PG3 else "psycopg2",
                "mode": "", "row_count": 0, "export_csv": "", "export_xlsx": "", "query_sha256": ""
            })
            self.app._last_test_ok = False

    def on_next(self):
        host = self.var_host.get().strip()
        port = self.var_port.get().strip()
        db   = self.var_db.get().strip()
        user = self.e_user.get().strip()
        pwd  = self.e_pwd.get().strip()
        outdir = self.e_out.get().strip()
        if not (host and port and db and user and pwd and outdir):
            messagebox.showerror("Missing input","Fill all fields and choose an output folder"); return
        if not os.path.isdir(outdir):
            messagebox.showerror("Output folder","Choose a valid directory"); return
        cfg = dict(self.app.selection["cfg"]); cfg["host"] = host
        self.app.selection.update({"host":host,"port":port,"db":db,"user":user,"pwd":pwd,"outdir":outdir,"cfg":cfg})
        self.app.show_utility()

class UtilityScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.inner = None
        pad = {"padx": 10, "pady": 8}
        ttk.Label(self, text="Utility").grid(row=0, column=0, sticky="w", **pad)
        ttk.Button(self, text="← Back", command=self.app.show_creds).grid(row=0, column=1, sticky="e", **pad)
        self.rowconfigure(1, weight=1); self.columnconfigure(0, weight=1); self.columnconfigure(1, weight=1)

    def load_utility(self):
        if self.inner is not None:
            self.inner.destroy(); self.inner = None
        util = self.app.selection.get("util")
        if util == "Payload Comparison":
            self.inner = PayloadComparisonFrame(self, self.app)
            schema = self.app.selection.get("cfg",{}).get("schema","sdc_owner")
            self.inner.load_defaults_from_selection(schema)
        else:
            self.inner = PlaceholderFrame(self, "Coming soon")
        self.inner.grid(row=1, column=0, columnspan=2, sticky="nsew")

class PlaceholderFrame(ttk.Frame):
    def __init__(self, master, text: str):
        super().__init__(master)
        ttk.Label(self, text=text).pack(padx=12, pady=12)

class PayloadComparisonFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.running = False
        pad = {"padx": 10, "pady": 6}

        drv = "psycopg v3" if HAVE_PG3 else ("psycopg2" if HAVE_PG2 else "none")
        ttk.Label(self, text=f"Driver: {drv} | OS: {'Windows' if os.name=='nt' else os.name}").grid(row=0, column=0, columnspan=8, sticky="w", **pad)

        ttk.Label(self, text="SQL (SELECT only)").grid(row=1, column=0, sticky="w", **pad)
        self.txt_sql = tk.Text(self, height=14, wrap="word")
        self.txt_sql.grid(row=2, column=0, columnspan=8, sticky="nsew", **pad)
        self.rowconfigure(2, weight=1)
        [self.columnconfigure(c, weight=1) for c in range(8)]

        self.var_copy = tk.IntVar(value=1)
        ttk.Checkbutton(self, text="Use COPY mode (keeps timestamps as text)", variable=self.var_copy).grid(row=3, column=0, sticky="w", **pad)

        self.var_autofix = tk.IntVar(value=1)
        ttk.Checkbutton(self, text="Auto-fix SQL ({schema}, first SELECT, trim ';')", variable=self.var_autofix).grid(row=3, column=1, sticky="w", **pad)

        self.btn_run = ttk.Button(self, text="Run Export → Launch Viewer", command=self.on_run)
        self.btn_run.grid(row=3, column=7, sticky="e", **pad)

        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.grid(row=3, column=4, columnspan=3, sticky="we", **pad)

        ttk.Label(self, text="Log").grid(row=4, column=0, sticky="w", **pad)
        self.txt_log = tk.Text(self, height=8)
        self.txt_log.grid(row=5, column=0, columnspan=8, sticky="nsew", **pad)
        self.rowconfigure(5, weight=1)

        self.lbl_hint = ttk.Label(self, text="Viewer auto-detected in the same folder (or PAYLOADDIFF_VIEWER_PATH).")
        self.lbl_hint.grid(row=6, column=0, columnspan=8, sticky="w", **pad)

    def load_defaults_from_selection(self, schema: str):
        self.txt_sql.delete("1.0", tk.END)
        self.txt_sql.insert("1.0", DEFAULT_SQL.format(schema=schema))

    def log(self, msg: str):
        self.after(0, lambda: (self.txt_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"),
                               self.txt_log.see(tk.END)))

    def set_running(self, on: bool):
        self.running = on
        if on:
            self.btn_run.configure(state=tk.DISABLED); self.pb.start(70)
        else:
            self.btn_run.configure(state=tk.NORMAL);  self.pb.stop()

    def on_run(self):
        if getattr(self.app, "_last_test_ok", False) is not True:
            messagebox.showwarning("Run disabled", "Please run Test Connection first (Credentials page).")
            return
        if self.running:
            return

        schema = self.app.selection.get("cfg",{}).get("schema","sdc_owner")
        sql = self.txt_sql.get("1.0", tk.END)

        if bool(self.var_autofix.get()):
            fixed, notes = auto_fix_sql(sql, schema)
            if fixed != sql:
                self.txt_sql.delete("1.0", tk.END); self.txt_sql.insert("1.0", fixed)
                for n in notes: self.log(f"auto-fix: {n}")
            sql = fixed

        ok, reason = validate_select_only(sql)
        if not ok:
            messagebox.showerror("Only SELECT allowed", reason); return

        sel = self.app.selection
        cfg = {"host":sel["host"], "port":int(sel["port"]), "dbname":sel["db"], "schema":schema}
        user, pwd, outdir = sel["user"], sel["pwd"], sel["outdir"]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(outdir) / f"payload_export_{ts}"
        outfile_csv  = base.with_suffix(".csv")
        outfile_xlsx = base.with_suffix(".xlsx")
        use_copy = bool(self.var_copy.get())

        self.set_running(True)
        threading.Thread(
            target=self._worker,
            args=(cfg, user, pwd, sql.strip(), outfile_csv, outfile_xlsx, use_copy, outdir),
            daemon=True
        ).start()

    def _worker(self, cfg, user, pwd, sql, outfile_csv: Path, outfile_xlsx: Path, use_copy: bool, outdir: str):
        import pandas as pd
        start = time.perf_counter()
        conn = None; tmpcsv = None; rowcount = 0; result = "success"; errmsg = ""

        try:
            self.log("Connecting to Postgres…")
            conn = connect_pg(cfg["host"], cfg["port"], cfg["dbname"], user, pwd)
            self.log("Connected (read-only).")

            # Fetch
            if use_copy:
                self.log("Using COPY → CSV stream")
                copy_sql = f"COPY ({sql}) TO STDOUT WITH CSV HEADER"
                fd, tmpcsv = tempfile.mkstemp(prefix="pg_export_", suffix=".csv"); os.close(fd)
                cur = conn.cursor()
                try:
                    if HAVE_PG3:
                        with open(tmpcsv, "wb") as f:
                            with cur.copy(copy_sql) as cp:
                                while True:
                                    chunk = cp.read()
                                    if not chunk: break
                                    f.write(chunk)
                    else:
                        with open(tmpcsv, "w", newline="", encoding="utf-8") as f:
                            cur.copy_expert(copy_sql, f)
                finally:
                    try: cur.close()
                    except Exception: pass
                df = pd.read_csv(tmpcsv, na_filter=False)
            else:
                self.log("Cursor fetch path")
                cur = conn.cursor()
                try:
                    cur.execute(sql); rows = cur.fetchall()
                    cols = []
                    for d in cur.description:
                        name = getattr(d, "name", None)
                        if name is None and isinstance(d, (tuple,list)) and len(d)>0: name = d[0]
                        if name is None: name = f"col_{len(cols)}"
                        cols.append(str(name))
                finally:
                    try: cur.close()
                    except Exception: pass
                df = pd.DataFrame(rows, columns=cols)

            rowcount = len(df)

            # Close DB before file I/O
            if conn is not None:
                try:
                    conn.close(); self.log("✅ Database connection closed."); conn = None
                except Exception as e:
                    self.log(f"Warn: close failed: {e}")

            if rowcount == 0:
                self.log("No rows returned.")
                self.after(0, messagebox.showinfo, "No data", "Query returned 0 rows.")
                return

            # Write CSV + XLSX
            df.to_csv(outfile_csv, index=False, encoding="utf-8")
            self.log(f"CSV written: {outfile_csv}")

            try:
                with pd.ExcelWriter(outfile_xlsx, engine="openpyxl") as xw:
                    df.to_excel(xw, index=False, sheet_name="data")
                self.log(f"✅ Excel written: {outfile_xlsx}")
            except Exception as e:
                self.log(f"Excel write failed: {e}")

            # Prefer XLSX; fallback to CSV
            preferred = outfile_xlsx if outfile_xlsx.exists() else outfile_csv
            self.after(0, messagebox.showinfo, "Export complete", f"Rows: {rowcount}\nLaunching viewer…")
            launched = launch_viewer(preferred, self.log)
            self.log("Viewer launched." if launched else "Viewer launch failed.")

        except Exception as e:
            result = "error"; errmsg = str(e); self.log(f"ERROR: {errmsg}")
            if "too many connections" in errmsg.lower():
                self.after(0, messagebox.showerror, "Connection pool full",
                           "Too many connections for your role. Close idle sessions or retry later.")
            else:
                self.after(0, messagebox.showerror, "Run failed", errmsg)
        finally:
            if conn is not None:
                try: conn.close(); self.log("Database connection closed (cleanup).")
                except Exception: pass
            if tmpcsv and os.path.exists(tmpcsv):
                try: os.remove(tmpcsv)
                except Exception: pass

            duration_ms = int((time.perf_counter() - start) * 1000)
            from hashlib import sha256
            qhash = sha256(sanitize_sql_for_log(sql).encode("utf-8","ignore")).hexdigest()

            # JSONL audit
            audit_write_jsonl({
                "ts_iso": datetime.now().isoformat(timespec="seconds"),
                "op":"run_export_launch","status":result,"error_message":errmsg,
                "host":cfg["host"],"port":cfg["port"],"db_name":cfg["dbname"],
                "driver":"psycopg3" if HAVE_PG3 else "psycopg2",
                "mode":"COPY" if use_copy else "cursor",
                "row_count": rowcount,"duration_ms": duration_ms,
                "export_csv": str(outfile_csv),"export_xlsx": str(outfile_xlsx),
                "query_sha256": qhash,"connection_closed": True
            })

            # CSV audit in output folder
            try:
                csv_path = audit_write_csv(outdir, {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "op": "run_export_launch", "status": result, "error_message": errmsg,
                    "duration_ms": duration_ms,
                    "region": self.app.selection.get("region"),
                    "environment": self.app.selection.get("env"),
                    "host": cfg.get("host"), "port": cfg.get("port"),
                    "db_name": cfg.get("dbname"), "schema": cfg.get("schema"),
                    "user": self.app.selection.get("user"),
                    "driver": "psycopg3" if HAVE_PG3 else "psycopg2",
                    "mode": "COPY" if use_copy else "cursor", "row_count": rowcount,
                    "export_csv": str(outfile_csv) if result == "success" else "",
                    "export_xlsx": str(outfile_xlsx) if result == "success" else "",
                    "query_sha256": qhash,
                })
                self.log(f"Audit CSV → {csv_path}")
            except Exception as ae:
                self.log(f"Audit CSV failed: {ae}")

            self.after(0, self.set_running, False)

# ------------------------ App shell ------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Payload Wizard {APP_VERSION}")
        self.geometry("1180x800")
        self.selection = {}
        self._last_test_ok = False
        self._last_outdir = ""

        self.parent = ParentScreen(self, self)
        self.creds  = CredsScreen(self, self)
        self.util   = UtilityScreen(self, self)
        self.parent.pack(fill=tk.BOTH, expand=True)

        # Menu-based test as well
        menubar = tk.Menu(self)
        act = tk.Menu(menubar, tearoff=0)
        act.add_command(label="Test Connection", command=self.test_connection_dialog)
        menubar.add_cascade(label="Actions", menu=act)
        self.config(menu=menubar)

    def show_parent(self):
        self.creds.pack_forget(); self.util.pack_forget()
        self.parent.pack(fill=tk.BOTH, expand=True)

    def show_creds(self):
        self.parent.pack_forget(); self.util.pack_forget()
        self.creds.pack(fill=tk.BOTH, expand=True)
        self.creds.load_from_selection()

    def show_utility(self):
        self.parent.pack_forget(); self.creds.pack_forget()
        self.util.pack(fill=tk.BOTH, expand=True)
        self.util.load_utility()

    def test_connection_dialog(self):
        if not self.selection:
            messagebox.showinfo("Info", "Pick Region/Env and enter credentials first.")
            return
        try:
            host = self.selection["host"]; port = int(self.selection["port"]); db = self.selection["db"]
            user = self.selection.get("user",""); pwd = self.selection.get("pwd",""); outdir = self.selection.get("outdir","")
        except Exception:
            messagebox.showinfo("Info", "Enter credentials on the Creds page first."); return
        if not outdir: outdir = str(Path.home())

        t0 = time.perf_counter()
        try:
            conn = connect_pg(host, port, db, user, pwd); conn.close()
            dt = int((time.perf_counter() - t0) * 1000)
            messagebox.showinfo("Connection OK", f"Connected successfully in {dt} ms.")
            audit_write_jsonl({"ts_iso":datetime.now().isoformat(timespec="seconds"),
                               "op":"test_connection","status":"success",
                               "host":host,"port":port,"db_name":db,
                               "driver":"psycopg3" if HAVE_PG3 else "psycopg2"})
            audit_write_csv(outdir, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "op": "test_connection", "status": "success", "error_message": "",
                "duration_ms": dt,
                "region": self.selection.get("region"),
                "environment": self.selection.get("env"),
                "host": host, "port": port, "db_name": db,
                "schema": self.selection.get("cfg",{}).get("schema",""),
                "user": user, "driver": "psycopg3" if HAVE_PG3 else "psycopg2",
                "mode": "", "row_count": 0, "export_csv": "", "export_xlsx": "", "query_sha256": ""
            })
            self._last_test_ok = True
            self._last_outdir = outdir
        except Exception as e:
            messagebox.showerror("Connection failed", str(e))
            audit_write_jsonl({"ts_iso":datetime.now().isoformat(timespec="seconds"),
                               "op":"test_connection","status":"error","error_message":str(e),
                               "host":host,"port":port,"db_name":db})
            audit_write_csv(outdir, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "op": "test_connection", "status": "error", "error_message": str(e),
                "duration_ms": 0,
                "region": self.selection.get("region"),
                "environment": self.selection.get("env"),
                "host": host, "port": port, "db_name": db,
                "schema": self.selection.get("cfg",{}).get("schema",""),
                "user": user, "driver": "psycopg3" if HAVE_PG3 else "psycopg2",
                "mode": "", "row_count": 0, "export_csv": "", "export_xlsx": "", "query_sha256": ""
            })
            self._last_test_ok = False

if __name__ == "__main__":
    App().mainloop()
