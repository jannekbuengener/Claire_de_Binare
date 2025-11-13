Param(
  [Parameter(Mandatory=$true)]
  [string[]]$Paths
)

$ErrorActionPreference = "Stop"

function Normalize-Markdown([string]$Text) {
  # 1) Setext H1/H2 -> ATX
  $text = $Text -replace "(?m)^(?<t>.+?)\r?\n=+\s*$",   "# ${t}`n"
  $text = $text -replace "(?m)^(?<t>.+?)\r?\n-+\s*$", "## ${t}`n"
  # 2) Trailing spaces
  $text = $text -replace "[ \t]+(`r?`n)", '$1'
  # 3) Nur eine H1 beibehalten (weitere H1 → H2)
  $lines = $text -split "`r?`n"
  $h1Idx = @()
  for ($i=0; $i -lt $lines.Length; $i++) { if ($lines[$i] -match '^\#\s+') { $h1Idx += $i } }
  if ($h1Idx.Count -gt 1) {
    for ($j=1; $j -lt $h1Idx.Count; $j++) {
      $idx = $h1Idx[$j]
      if ($lines[$idx] -match '^\#\s+') { $lines[$idx] = $lines[$idx] -replace '^\#\s+', '## ' }
    }
    $text = [string]::Join("`n", $lines)
  }
  return $text
}

function Process-File([string]$FilePath) {
  $orig = Get-Content -Raw -Encoding UTF8 -Path $FilePath
  $norm = Normalize-Markdown $orig
  if ($norm -ne $orig) {
    Set-Content -Path $FilePath -Value $norm -Encoding UTF8 -NoNewline:$false
    return $true
  }
  return $false
}

$changed = 0
foreach ($p in $Paths) {
  if (Test-Path $p -PathType Container) {
    Get-ChildItem $p -Recurse -Filter *.md | ForEach-Object { if (Process-File $_.FullName) { $changed++ } }
  } elseif (Test-Path $p -PathType Leaf -and ([IO.Path]::GetExtension($p) -ieq ".md")) {
    if (Process-File (Resolve-Path $p)) { $changed++ }
  }
}
Write-Host "Normalized files: $changed"
