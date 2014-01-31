##
# Copyright 2010-2013 Enstratius Inc. 
#
# This software is part of the Enstratius Cloud Management System. Only 
# authorized licensees of Enstratius may use this software and only
# in the context of Enstratius-managed virtual servers and machine images. 
# Unauthorized copying or distribution of this software is strictly prohibited.
# Authorized licensees may copy this software onto any machine images
# and/or virtual hosts being managed by the Enstratius system as needed.
#
# FUNCTION
# Call this script to set java environment variable and run enstratus agent installed by windows installer.

#Change powershell's execution policy to make scripts available.

Set-ExecutionPolicy Unrestricted

$logfile="C:\es-agent-ps.log"
$ErrorActionPreference = "Stop"

try {
	#Find Java home directory.
	$javaHome=$env:JAVA_HOME

	if( $javaHome -eq $null -or !(Test-Path "$javaHome\bin\javac.exe") ) {
		$javac=Get-ChildItem "c:\Program Files" -recurse | where {$_.Name -eq "javac.exe"}
		if( $javac -is [System.Array] ) {
			$javac=$javac[0]
		}
		$javaHome=$javac.directory.parent.fullName
	}

	#Set environment variables for Java and Tomcat.
	$env:JAVA_HOME="$javaHome"
	$env:CATALINA_BASE="c:\enstratus\ws\tomcat"
	$env:CATALINA_HOME=$env:CATALINA_BASE
	$env:TOMCAT5_SECURITY="no"

	#Stop and Remove existing enstratus service.
	if (Get-Service "enstratus" -ErrorAction SilentlyContinue)
	{
	    Stop-Service enstratus
	    $service = Get-WmiObject -Class Win32_Service -Filter "Name='enstratus'"
	    $service.delete()
	}

	#Register enstratus service.
	& $env:CATALINA_BASE\bin\service.bat install enstratus

	#Set enstratus service's startup type to Automatic(delayed). This doesn't work in old Windows 2003 server family.
	Set-ItemProperty -Path "Registry::HKLM\System\CurrentControlSet\Services\enstratus" -Name "DelayedAutostart" -Value 1 -Type DWORD

	#Start enstratus service.
	echo "Starting Enstratius Tomcat process on port 2003..."
	cd C:\enstratus
	Start-Service enstratus
	echo "Done."
} catch {
	Add-Content $logfile -value $error
	exit 1000
} finally {
	$ErrorActionPreference = "Continue"
}
