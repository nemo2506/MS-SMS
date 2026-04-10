#!/bin/bash

source ~/miniconda3/etc/profile.d/conda.sh
conda activate saule-client

cd /home/marc/data/projets/plugins-python/ms_sms/
python test_ms_sms.py
