# sync-subrepos.ps1
#
# Publishes slices of this monorepo into the standalone sub-repos.
#
#   .\sync-subrepos.ps1 -Target forge-puzzles -WhatIf     # show, change nothing
#   .\sync-subrepos.ps1 -Target forge-puzzles
#   .\sync-subrepos.ps1 -Target all
#
# The split follows TibetSwap's: on-chain code that an auditor reads lives apart
# from the interface built on top of it (github.com/Yakuhito/tibet vs tibet-ui).
# Two reasons, and only the second is about tidiness:
#
#   1. An auditor should be able to read everything that can move funds without
#      also reading a React app. What is in the puzzle repo IS the attack
#      surface; anything else in there dilutes that claim.
#   2. The puzzle repos can go public while the interface stays private.
#
# This script only ever COPIES OUT. The monorepo is the source of truth; nothing
# is ever read back from a sub-repo. Committing and pushing stays manual and
# deliberate, because these destinations are public.
#
# Every slice is explicit. There is no "copy the rest" rule, because the failure
# mode here is publishing something nobody meant to publish.

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("forge-puzzles", "forge-ui", "greenwood-puzzles", "greenwood-ui", "all")]
    [string]$Target = "all",

    [Parameter(Mandatory = $false)]
    [switch]$WhatIf,

    [Parameter(Mandatory = $false)]
    [switch]$Detailed
)

$ErrorActionPreference = "Stop"

$MainDir = "C:\Users\Ricardo\Documents\discord\aWizard-Familiar"
# Each family of repos sits under its own root, because that is how they were
# cloned. A repo spec may override with its own Root.
$ForgeRoot     = "C:\Users\Ricardo\Documents\The Forge"
$GreenwoodRoot = "C:\Users\Ricardo\Documents\greenwood"
$Org     = "awizardxch"

# Never copied, whatever a slice asks for. Build output, dependencies, local
# chain state, and anything holding a key.
$AlwaysExclude = @(
    "node_modules", "dist", "build", ".next", "out", ".vite", ".git",
    "__pycache__", ".pytest_cache", ".simulator", ".awizard", "memories",
    "artifacts", "cache"
)

# Files that are working detritus rather than source: one-off bundles kept while
# chasing a bug, error dumps from failed runs. Harmless in the monorepo, noise in
# a repository someone has been asked to audit -- and `debug_bundle.json` reads
# like an invitation to look at the wrong thing.
$AlwaysExcludeFiles = @(
    ".env", "*.log", "debug_*.json", "*_error_*.json",
    "cancel_body*.json", "cancel_result*.json", "lifecycle_*.json"
)

# ── the slices ──────────────────────────────────────────────────────────────
#
# From is relative to $MainDir, To is relative to the sub-repo root. A slice may
# name a directory or a single file.

$Repos = [ordered]@{
    "forge-puzzles" = @{
        Root        = $ForgeRoot
        Description = "Forge's on-chain code: the V13 pool on CHIP-0050, the lock, and every suite that runs them."
        # Published by an earlier sync, when the slice still shipped the previous
        # revision. Named here so the next sync takes them back out.
        Prune       = @(
            "contracts\v11", "contracts\_test_v11_*.py",
            "docs\FORGE_PUZZLE_V11.md", "docs\FORGE_V11_ARCHITECTURE.md",
            "docs\FORGE_V11_CLVM_PASS.md", "docs\FORGE_V11_FOUNDATIONS.md",
            "scripts\mutate-v11.py", "scripts\build-v11.py",
            # V12 was retired by a second independent review on 2026-09-14, which
            # demonstrated a full drain of an unregistered pool against it. Its sources
            # come back out for the reason V11's did: a working recipe against dead code
            # helps an attacker practising against the live revision and helps a reviewer
            # not at all.
            "contracts\v12", "contracts\_test_v12_*.py", "contracts\forge_v12_*.py",
            "contracts\_v12_testkit.py", "docs\FORGE_PUZZLE_V12.md",
            "scripts\mutate-v12.py", "scripts\build-v12.py",
            "docs\FORGE_V11_ARCHITECTURE.md", "docs\FORGE_V11_CLVM_PASS.md",
            "docs\FORGE_DAO_FEE_V11.md"
        )
        Visibility  = "public"
        Slices      = @(
            # `development` holds retired revisions. They are excluded deliberately:
            # publishing working exploit mechanics for dead code helps an attacker
            # practising against the live one and helps a reviewer not at all. The
            # record is in the private findings log, to be published with the
            # audit request. See docs/subrepo/forge-puzzles.SECURITY.md.
            # `development` was the only thing this rule named, but the previous revision's
            # sources sit at contracts\v11, one level above it, and its suites sit beside
            # them as contracts\_test_v11_*.py -- so both were published while the comment
            # above said they were not. The retired pools are also a live honeypot: their
            # LP was burned on purpose so that ANY movement is evidence of the drain class
            # the review named, and a published recipe would spoil that the day it went up.
            @{ From = "projects\chia-cfmm\contracts"; To = "contracts"
               Except = @("greenwood", "development", "v11", "v12")
               # _curve_mirror_cases.json is regenerated by every `node scripts/run-checks.mjs`;
               # it is a 10,000-line artefact of the check, not source.
               # _test_v12_v13_review_findings.py exploits contracts\v12 and is excluded
               # with the revision it exploits, exactly as the V11/V12 pair was.
               ExceptFiles = @("_test_v11_*.py", "_test_v12_*.py", "forge_v12_*.py",
                               "_v12_testkit.py", "_curve_mirror_cases.json") }
            @{ From = "projects\chia-cfmm\docs\FORGE_PUZZLE_V13.md";      To = "docs\FORGE_PUZZLE_V13.md" }
            # The CHIP's Additional Assets links these two by name. Publishing the
            # specification without them leaves the list pointing at nothing, which is the
            # failure revision 3 had to correct for the V11 set.
            @{ From = "projects\chia-cfmm\docs\FORGE_V13_ARCHITECTURE.md"; To = "docs\FORGE_V13_ARCHITECTURE.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_V13_CLVM_PASS.md";   To = "docs\FORGE_V13_CLVM_PASS.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_AUDIT_TIBETSWAP.md"; To = "docs\FORGE_AUDIT_TIBETSWAP.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_CHIP_WORKFLOW.md";   To = "docs\FORGE_CHIP_WORKFLOW.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_ROUTER_PROTOCOL_V1.md"; To = "docs\FORGE_ROUTER_PROTOCOL_V1.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_MULTISIG.md";        To = "docs\FORGE_MULTISIG.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_LOCK_MIPS.md";       To = "docs\FORGE_LOCK_MIPS.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_LOCK_SAFE_MODEL.md"; To = "docs\FORGE_LOCK_SAFE_MODEL.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_DAO_FEE_V13.md";     To = "docs\FORGE_DAO_FEE_V13.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.SECURITY.md"; To = "docs\FORGE_SECURITY.md" }
            @{ From = "projects\chia-cfmm\docs\chip";  To = "docs\chip" }
            # FORGE_SECURITY.md and the CHIP's Test Cases section both cite this
            # by path; it ships so those references resolve.
            @{ From = "projects\chia-cfmm\scripts\mutate-v13.py"; To = "scripts\mutate-v13.py" }
            @{ From = "projects\chia-cfmm\scripts\build-v13.py";  To = "scripts\build-v13.py" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.gitignore"; To = ".gitignore" }
        )
    }

    "forge-ui" = @{
        Root        = $ForgeRoot
        Description = "forge.awizard.dev: the interface and the off-chain services around the puzzles."
        Visibility  = "private for now"
        Slices      = @(
            @{ From = "projects\chia-cfmm\src";     To = "src" }
            @{ From = "projects\chia-cfmm\api";     To = "api" }
            @{ From = "projects\chia-cfmm\public";  To = "public" }
            @{ From = "projects\chia-cfmm\scripts"; To = "scripts" }
            # Not the monorepo's package.json: that one is named chia-cfmm-local and its
            # scripts reach into contracts\ and ..\..\.venv, neither of which exists here.
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.package.json"; To = "package.json" }
            @{ From = "projects\chia-cfmm\package-lock.json"; To = "package-lock.json" }
            @{ From = "projects\chia-cfmm\tsconfig.json";     To = "tsconfig.json" }
            # index.html references tsconfig.node.json; without it `vite build` fails
            # before transforming a single module.
            @{ From = "projects\chia-cfmm\tsconfig.node.json"; To = "tsconfig.node.json" }
            @{ From = "projects\chia-cfmm\vite.config.ts";    To = "vite.config.ts" }
            @{ From = "projects\chia-cfmm\index.html";        To = "index.html" }
            @{ From = "projects\chia-cfmm\vercel.json";       To = "vercel.json" }
            @{ From = "projects\chia-cfmm\docs\FORGE_SWAP.md";      To = "docs\FORGE_SWAP.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_LIQUIDITY.md"; To = "docs\FORGE_LIQUIDITY.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_MARKETS.md";   To = "docs\FORGE_MARKETS.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_BALANCER.md";  To = "docs\FORGE_BALANCER.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_DEPLOY_POOL.md"; To = "docs\FORGE_DEPLOY_POOL.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.gitignore"; To = ".gitignore" }
        )
    }

    "greenwood-puzzles" = @{
        Root        = $GreenwoodRoot
        Description = "Greenwood's on-chain code, both chains: the Chia puzzle an Ethereum key can spend, and the Solidity beside it."
        Visibility  = "public"
        Slices      = @(
            @{ From = "projects\chia-cfmm\contracts\greenwood"; To = "chia" }
            @{ From = "projects\greenwood\evm";                 To = "evm" }
            @{ From = "projects\greenwood\docs";                To = "docs" }
            @{ From = "projects\chia-cfmm\docs\subrepo\greenwood-puzzles.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\greenwood-puzzles.gitignore"; To = ".gitignore" }
        )
    }

    "greenwood-ui" = @{
        Root        = $GreenwoodRoot
        Description = "greenwood.awizard.dev: the front end and the server around the Greenwood puzzles."
        Visibility  = "private for now"
        Slices      = @(
            @{ From = "projects\greenwood\src";    To = "src" }
            @{ From = "projects\greenwood\server"; To = "server" }
            @{ From = "projects\greenwood\public"; To = "public" }
            @{ From = "projects\greenwood\scripts"; To = "scripts" }
            @{ From = "projects\greenwood\package.json";      To = "package.json" }
            @{ From = "projects\greenwood\package-lock.json"; To = "package-lock.json" }
            @{ From = "projects\greenwood\tsconfig.json";     To = "tsconfig.json" }
            @{ From = "projects\greenwood\vite.config.ts";    To = "vite.config.ts" }
            @{ From = "projects\greenwood\index.html";        To = "index.html" }
            @{ From = "projects\chia-cfmm\docs\subrepo\greenwood-ui.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\greenwood-ui.gitignore"; To = ".gitignore" }
        )
    }
}

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Copy-Slice {
    param([hashtable]$Slice, [string]$Destination)

    $source = Join-Path $MainDir $Slice.From
    if (-not (Test-Path $source)) {
        Write-Status "    ! missing, skipped: $($Slice.From)" "Yellow"
        return
    }
    $target = Join-Path $Destination $Slice.To

    if (Test-Path $source -PathType Leaf) {
        if ($Detailed) { Write-Status "    file  $($Slice.From) -> $($Slice.To)" "DarkGray" }
        if (-not $WhatIf) {
            New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
            Copy-Item $source $target -Force
        }
        return
    }

    if ($Detailed) { Write-Status "    dir   $($Slice.From)\ -> $($Slice.To)\" "DarkGray" }
    if ($WhatIf) { return }

    New-Item -ItemType Directory -Force -Path $target | Out-Null
    $exclude = $AlwaysExclude + @($Slice.Except | Where-Object { $_ })
    $excludeFiles = $AlwaysExcludeFiles + @($Slice.ExceptFiles | Where-Object { $_ })
    $args = @($source, $target, '/E', '/PURGE', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
              '/XD') + $exclude + @('/XF') + $excludeFiles
    & robocopy @args | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "robocopy failed for $($Slice.From) (exit $LASTEXITCODE)" }
}

function Sync-Repo {
    param([string]$Name)

    $spec = $Repos[$Name]
    $dir  = Join-Path $spec.Root $Name

    Write-Status "`n$Name  ($($spec.Visibility))" "Cyan"
    Write-Status "  $($spec.Description)" "Gray"

    if (-not (Test-Path $dir)) {
        Write-Status "  x not cloned yet: $dir" "Red"
        Write-Status "    Create it on GitHub, then:" "Yellow"
        Write-Status "      git clone https://github.com/$Org/$Name.git `"$dir`"" "DarkYellow"
        return
    }

    # Excluding a path stops it being COPIED; it does not remove what an earlier sync
    # already wrote, because robocopy skips an excluded directory entirely and never
    # considers it for /PURGE. So a slice that stops publishing something has to say so
    # out loud, or the thing it stopped publishing quietly stays published.
    foreach ($gone in @($spec.Prune | Where-Object { $_ })) {
        $stale = Join-Path $dir $gone
        foreach ($hit in @(Get-Item -Path $stale -ErrorAction SilentlyContinue)) {
            if ($WhatIf) {
                Write-Status "    prune $($hit.FullName.Substring($dir.Length + 1))" "DarkYellow"
            } else {
                Remove-Item -Recurse -Force -LiteralPath $hit.FullName
                Write-Status "    pruned $($hit.FullName.Substring($dir.Length + 1))" "Yellow"
            }
        }
    }

    foreach ($slice in $spec.Slices) { Copy-Slice -Slice $slice -Destination $dir }

    if ($WhatIf) {
        Write-Status "  (dry run — nothing written)" "DarkGray"
    } else {
        Write-Status "  synced -> $dir" "Green"
    }
}

Write-Status "`nForge sub-repo sync" "Magenta"
Write-Status "-------------------" "Magenta"
if ($WhatIf) { Write-Status "DRY RUN: showing what would be copied, writing nothing." "Yellow" }

$targets = if ($Target -eq "all") { $Repos.Keys } else { @($Target) }
foreach ($name in $targets) { Sync-Repo -Name $name }

Write-Status "`nNothing was committed or pushed." "Yellow"
Write-Status "Review each sub-repo, then commit and push it yourself:" "Gray"
Write-Status "  cd <repo> ; git status ; git add -A ; git commit ; git push" "DarkGray"
Write-Status ""
