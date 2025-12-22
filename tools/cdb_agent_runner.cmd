@echo off
setlocal
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 "%~dp0cdb_agent_runner.py" %*
  exit /b %ERRORLEVEL%
)
python "%~dp0cdb_agent_runner.py" %*
exit /b %ERRORLEVEL%
