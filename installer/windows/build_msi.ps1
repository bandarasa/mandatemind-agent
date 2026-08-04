param(
    [string]$SolutionRoot = "$(Split-Path -Parent $PSScriptRoot)\..",
    [string]$OutputMsi = "$(Split-Path -Parent $PSScriptRoot)\MandateMindAgentSetup.msi"
)

$wixBin = "$PSScriptRoot\wix"
$candle = Join-Path $wixBin "candle.exe"
$light  = Join-Path $wixBin "light.exe"

Write-Host "[MandateMind] Building Windows MSI..."

# Paths to WiX sources
$wxsMain   = Join-Path $PSScriptRoot "MandateMindAgent.wxs"
$wxsProd   = Join-Path $PSScriptRoot "Product.wxs"
$wxsHeat   = Join-Path $PSScriptRoot "heat-collectors.wxs"

# Compile
& $candle -nologo $wxsMain $wxsProd $wxsHeat

# Link
& $light -nologo -ext WixUtilExtension MandateMindAgent.wixobj Product.wixobj heat-collectors.wixobj -o $OutputMsi

Write-Host "[MandateMind] MSI created at: $OutputMsi"
