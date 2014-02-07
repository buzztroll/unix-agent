@echo off
rem Enstratius Windows Agent Silent Installer.
rem Updated on 15 Mar 2013.
rem Maintainer: sean.kang@enstratius.com
rem Put this script into the working directory where the msi installer is located and run it.
rem This script was tested with windows agent msi installer > 17.4
rem Prerequiste programs to silently install the agent are as below.
rem Windows Server 2003, 2008: JDK 7

rem Validating parameteres.

set argC=0
for %%x in (%*) do set /A argC+=1

if %argC% LSS 3 (
	echo Illegal options.
	echo "Usage: install [Amazon|Atmos|ATT|Azure|Bluelock|CloudCentral|CloudSigma|CloudStack|CloudStack3|Eucalyptus|GoGrid|Google|IBM|Joyent|OpenStack|Rackspace|ReliaCloud|ServerExpress|Terremark|VMware|Other] [production|staging] [ProvisioningIP or DomainName] /p=[Provisioning port(optional, default=3302) /m=[Metadata(optional)] /u=[Userdata(optional)] /t=[Handshake time(optional)]"
	echo "Example: install Amazon production provisioning.enstratus.com"
	goto :EOF
)

rem Setting compulsory parameters.

set CSP=%1
set TYPE=%2
set PROVIP=%3

rem Setting default values of optional parameters.

set PROVPORT=3302
set METADATA="latest/instance-id"
set USERDATA="169.254.169.254/1.0/meta-data"
set HANDSHAKE=5

rem Detecting and setting optional parameters.

if %argC% == 3 goto :END

:LOOP_START
set temp=%4
set flag=%temp:~0,2%

if %flag% == /p (
	set PROVPORT=%5%
	goto :CONTINUE
) else if %flag% == /m (
	set METADATA=%5%
	goto :CONTINUE
) else if %flag% == /u (
	set USERDATA=%5%
	goto :CONTINUE
) else if %flag% == /t (
	set HANDSHAKE=%5%
	goto :CONTINUE
)

:CONTINUE
SHIFT
if "%4" == "" GOTO END
GOTO :LOOP_START

:END

rem Running installer with valid parameters.

echo Installing Enstratius Agent for Windows.
echo Please wait...

enstratus-agent-windows-generic.exe /exenoui /qn /L*v "C:\es-agent-msi.log" MANUAL="1" LISTBOX_1_PROP=%CSP% RADIOBUTTONGROUP_1_PROP=%TYPE% EDIT_1_PROP=%PROVIP% EDIT_2_PROP=%PROVPORT% METADATA_PROP=%METADATA:/i=//ii% USERDATA_PROP=%USERDATA:/i=//ii% HANDSHAKE=%HANDSHAKE%

if %errorlevel% == 0 (
	echo Installation completed.
) else if %errorlevel% == 9009 (
	echo Installation failed. Error Level: %errorlevel%
	echo Program not found: enstratus-agent-windows-generic.exe
) else if %errorlevel% == 1625 (
	echo Installation failed. Error Level: %errorlevel%
	echo Run the installer as administrator.
) else (
	echo Installation failed. Error Level: %errorlevel%
	echo Please make sure to:
	echo 1. install JDK 7 prior to run the enstratus agent installer.
	echo 2. run the installer as administrator.
)

exit /b %errorlevel%
