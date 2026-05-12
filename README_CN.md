项目介绍：Commit2Code（仅支持 Java，已移除 Python 解析模式）
项目启动方式：在 Commit2Code 目录下运行 python find_codes.py --report /path/to/report.json --project /path/to/java/project
重构前后代码存放地址：Commit2Code/refacting_source_code
linux 环境下保证终端输出的同时记录运行日志 run.log: python find_codes.py --report /path/to/report.json --project /path/to/java/project 2>&1 | tee run.log


cd /root/workplace/Commit2Code
python find_codes.py

