param(
    [string]$SolutionRoot = "$(Split-Path -Parent $PSScriptRoot)\..",
    [string]$OutputMsi = "$(Split-Path -Parent $PSScriptRoot)\MandateMindAgentSetup.msi"
)

# Use system-installed WiX Toolset
$wixPath = "C:\Program Files (x86)\WiX Toolset v3.14\bin"

$candle = Join-Path $wixPath "candle.exe"
$light  = Join-Path $wixPath "light.exe"
$heat   = Join-Path $wixPath "heat.exe"

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
