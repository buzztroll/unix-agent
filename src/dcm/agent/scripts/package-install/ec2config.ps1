# Amazon-specific script.

$logfile="C:\es-agent-ps.log"
$EC2SettingsFile="C:\Program Files\Amazon\Ec2ConfigService\Settings\Config.xml"
$ErrorActionPreference = "Stop"
try {
	# Modify EC2 Config Tool's default setting not to conflict with enstratius agent.
	$xml = [xml](get-content $EC2SettingsFile)
	$xmlElement = $xml.get_DocumentElement()
	$xmlElementToModify = $xmlElement.Plugins

	foreach ($element in $xmlElementToModify.Plugin)
	{
	    if ($element.name -eq "Ec2InitializeDrives")
	    {
		$element.State="Disabled"
	    }
	    elseif ($element.name -eq "Ec2SetDriveLetter")
	    {
		$element.State="Disabled"
	    }
	}
	$xml.Save($EC2SettingsFile)

	# Disable automount and set up SAN policy.
	$os=Get-WmiObject -Class win32_OperatingSystem
	$onlineScript="C:\online.scr"
	if( $os.Version.StartsWith("6"))
	{
		echo "SAN POLICY=OnlineAll" | Out-File -encoding ASCII -append -filepath $onlineScript
	}
	echo "automount disable" | Out-File -encoding ASCII -append -filepath $onlineScript
	echo "automount scrub" | Out-File -encoding ASCII -append -filepath $onlineScript
	diskpart /s $onlineScript | out-null
	rm $onlineScript
} catch {
	Add-Content $logfile -value $error
	# exit with code 0 since it is not a critical error in non-amazon cloud that uses Amazon as identifier.
	exit 0
} finally {
	$ErrorActionPreference = "Continue"
}
