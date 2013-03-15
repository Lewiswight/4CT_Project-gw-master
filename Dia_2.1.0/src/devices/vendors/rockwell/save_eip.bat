REM Rockwell Ethernet/IP (PCCC only) Import Client 1.0

mkdir eip_diff\src\devices\vendors\rockwell

copy make.bat eip_diff
copy run.bat eip_diff

mkdir eip_diff\cfg\
copy cfg\eip_poller.yml      eip_diff\cfg

for %%X in (__init__.py, _test_eip_cmds.py, _test_pccc_util.py, cip.py, eip.py, eip_pccc_client.py, pccc_util.py, sleep_aids.py) do copy src\devices\vendors\rockwell\%%X eip_diff\src\devices\vendors\rockwell
