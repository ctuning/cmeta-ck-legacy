@echo off
rem Extract the 55 MILEPOST static features of C programs with the cMeta task
rem extract-milepost-features-legacy - Windows (Docker Desktop running).
rem
rem   _run.bat                   the two examples of this note; the reference one is checked
rem   _run.bat my.c other.c      your programs (C89 / GNU89, at most 64 KiB)
rem   _run.bat --engine=podman   any option starting with -- goes to the task
rem
rem The results go to results\ beside this file (set MILEPOST_RESULTS=<folder> for another one).
rem The first run on a machine downloads the capsules from https://doi.org/10.5281/zenodo.24246695.

setlocal EnableExtensions DisableDelayedExpansion

set "HERE=%~dp0"
if not defined MILEPOST_RESULTS set "MILEPOST_RESULTS=%HERE%results"
set "TASK=extract-milepost-features-legacy,4e719bc8239d4ece"
set "REFERENCE=%HERE%reference\example.c"
set "OPTIONS="
set "PROGRAMS="
set "STATUS=0"

rem Options (--...) go to the task, everything else is a program.
:args
if "%~1"=="" goto run
set "ARG=%~1"
if not "%ARG:~0,2%"=="--" goto program

rem cmd splits --name=value at the "=": join the value back unless the next word is a C file or an option.
set "NEXT=%~2"
if not defined NEXT goto option
if "%NEXT:~0,2%"=="--" goto option
if /i "%~x2"==".c" goto option
set "ARG=%ARG%=%~2"
shift

:option
set OPTIONS=%OPTIONS% "%ARG%"
shift
goto args

:program
set PROGRAMS=%PROGRAMS% "%~f1"
shift
goto args

:run
if not defined PROGRAMS set PROGRAMS="%HERE%examples\vector-stats.c" "%REFERENCE%"
if not exist "%MILEPOST_RESULTS%" mkdir "%MILEPOST_RESULTS%"

for %%P in (%PROGRAMS%) do call :extract "%%~P"

rem The reference program must give the values extracted on 2026-10-20 with the original installation.
for %%P in (%PROGRAMS%) do if /i "%%~P"=="%REFERENCE%" call :check

exit /b %STATUS%

:extract
echo.
echo === %~1 -^> %MILEPOST_RESULTS%\%~n1.features.json
call cx task run %TASK% --source-file="%~1" --output-file="%MILEPOST_RESULTS%\%~n1.features.json" %OPTIONS% -q
if errorlevel 1 set "STATUS=1"
goto :eof

:check
echo.
python "%HERE%compare.py" "%MILEPOST_RESULTS%\example.features.json" "%HERE%reference\example.features.json"
if errorlevel 1 set "STATUS=1"
goto :eof
