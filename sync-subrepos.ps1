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
    # ".env.*" covers the per-host files scripts/make-deploy-env.mjs writes.
    # They hold a whole deployment's configuration and belong in a dashboard,
    # not in a repository. The template still travels: it is named as its own
    # file slice, and a file slice is copied directly rather than through the
    # exclusion filter.
    ".env", ".env.*", "*.log", "debug_*.json", "*_error_*.json",
    "cancel_body*.json", "cancel_result*.json", "lifecycle_*.json"
)

# forge-ui is the deployment repo: the newest revision and the files the host
# and router need, nothing else. What contracts/ leaves behind is declared in
# the project rather than here, so the sync and the check that guards it cannot
# disagree -- api/__checks__/uiSliceClosure.check.mjs reads the same file and
# fails if a pattern would remove something the responder imports.
$ForgeUiPruneFile = Join-Path $MainDir "projects\chia-cfmm\docs\subrepo\forge-ui.contracts-prune.json"
$ForgeUiPrune = Get-Content $ForgeUiPruneFile -Raw | ConvertFrom-Json

# ── the slices ──────────────────────────────────────────────────────────────
#
# From is relative to $MainDir, To is relative to the sub-repo root. A slice may
# name a directory or a single file.

$Repos = [ordered]@{
    "forge-puzzles" = @{
        Root        = $ForgeRoot
        Description = "Forge's on-chain code: the V14 pool on CHIP-0050, the lock, and every suite that runs them."
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
            "docs\FORGE_DAO_FEE_V11.md",
            # V13 was retired by the fourth review on 2026-09-15 (a registration that
            # never funds its reserves takes a market key forever). Its sources come out
            # for the reason V11's and V12's did; its documents were published with
            # errata and come out with it, the errata now living in the V14 set.
            "contracts\v13", "contracts\_test_v13_*.py", "contracts\forge_v13_*.py",
            "contracts\_v13_testkit.py", "docs\FORGE_PUZZLE_V13.md",
            "docs\FORGE_V13_ARCHITECTURE.md", "docs\FORGE_V13_CLVM_PASS.md",
            "docs\FORGE_DAO_FEE_V13.md", "scripts\mutate-v13.py", "scripts\build-v13.py",
            # review-v13-security.py was sitting UNTRACKED in the public clone, named by
            # no slice, and `git add -A` would have published it. It probes the retired
            # V13 for phantom-reserve admission and imports _v13_testkit.py, which this
            # same list prunes -- so it would have shipped broken AND as exploit mechanics
            # for dead code. Named here so a stray copy cannot come back.
            "scripts\review-v13-security.py",
            # Dropping a file from the Slices above stops it being COPIED and does not remove
            # the copy already committed -- the exact gate failure that once left a retired
            # revision public while the comment said it was not. v14-route-audit.py quotes
            # routes on live pool states through our wallet driver, no published document
            # cites it, and it could not run there; it is named here so it actually leaves.
            "scripts\v14-route-audit.py"
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
               Except = @("greenwood", "development", "v11", "v12", "v13")
               # _curve_mirror_cases.json is regenerated by every `node scripts/run-checks.mjs`;
               # it is a 10,000-line artefact of the check, not source.
               # _test_v12_v13_review_findings.py exploits contracts\v12 and is excluded
               # with the revision it exploits, exactly as the V11/V12 pair was.
               # V14 shipped 2026-09-16: the design simulations that settled it publish with
               # it (the R-1 routes, the settlement binding, the review corrections), because
               # a rejected route is evidence. What stays private: the simulations of ideas
               # that are NOT built -- the fractionalised vault, the revocable and fee-layer
               # CATs (FORGE_PROJECTS.md) -- and the matrix JSON the simulator page reads.
               # _test_v13_second_review.py is superseded by _test_v14_second_review.py and
               # _test_v14_before_after.py, which run both builds.
               # _test_v14_chip0062_audit.py is named for V14 and so would have been
               # copied by the pattern below, but it BUILDS the CHIP-0062 audit's findings
               # against contracts\v11 before refusing them on V14 -- the two genesis
               # eves, the cross-leaf drain -- which is working exploit mechanics for a
               # retired revision, the one thing this slice exists to prevent. Its V14 half
               # is public anyway, in _test_v14_second_review.py and _test_v14_before_after.py.
               # An earlier version of this comment added that the file would ship BROKEN
               # too, because _v11_testkit.py is pruned. It is NOT -- see the note under
               # ExceptFiles, which exists to keep exactly that claim true. The testkit is
               # public and the attacks are built through the production driver, so the file
               # would have RUN there and reproduced them. That makes the exclusion more
               # necessary, not less.
               ExceptFiles = @("_test_v11_*.py", "_test_v12_*.py", "forge_v12_*.py",
                               "_v12_testkit.py", "_test_v13_*.py", "forge_v13_*.py",
                               "_v13_testkit.py", "_test_v14_chip0062_audit.py",
                               "_curve_mirror_cases.json",
                               "_sim_future_*", "_sim_v14_vault_*", "_sim_v14_rcat_*",
                               "_sim_v14_layered_*", "_sim_v14_matrix*") }
               # NOT pruned, and the comment above would otherwise be false: nine
               # contracts\forge_v11_*.py modules plus _v11_testkit.py and
               # v11_create_bridge.py stay public, because live code still needs them.
               # forge_v11_names.py is the ONLY name resolver there has ever been and
               # forge_v14_index.chain_names calls it; _v11_testkit.py is the control in
               # _test_v14_consensus_timelocks.py, which proves V11 asserted no birth
               # height where V14 does. What is excluded is what makes V11 runnable as a
               # protocol: contracts\v11 (its compiled puzzles) and _test_v11_*.py. So
               # v11_available() is false here and that control skips.
               # Worth fixing properly: rename forge_v11_names.py to forge_names.py, so a
               # version-agnostic helper stops being filed under a retired revision.
            @{ From = "projects\chia-cfmm\docs\FORGE_PUZZLE_V14.md";      To = "docs\FORGE_PUZZLE_V14.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_PUZZLE_V14_SPEC.md"; To = "docs\FORGE_PUZZLE_V14_SPEC.md" }
            # The CHIP's Additional Assets links these two by name. Publishing the
            # specification without them leaves the list pointing at nothing, which is the
            # failure revision 3 had to correct for the V11 set.
            @{ From = "projects\chia-cfmm\docs\FORGE_V14_ARCHITECTURE.md"; To = "docs\FORGE_V14_ARCHITECTURE.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_V14_CLVM_PASS.md";   To = "docs\FORGE_V14_CLVM_PASS.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_AUDIT_TIBETSWAP.md"; To = "docs\FORGE_AUDIT_TIBETSWAP.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_CHIP_WORKFLOW.md";   To = "docs\FORGE_CHIP_WORKFLOW.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_ROUTER_PROTOCOL_V1.md"; To = "docs\FORGE_ROUTER_PROTOCOL_V1.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_MULTISIG.md";        To = "docs\FORGE_MULTISIG.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_LOCK_MIPS.md";       To = "docs\FORGE_LOCK_MIPS.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_LOCK_SAFE_MODEL.md"; To = "docs\FORGE_LOCK_SAFE_MODEL.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_DAO_FEE_V14.md";     To = "docs\FORGE_DAO_FEE_V14.md" }
            # The record of an audit run made with the runbook in skills/, against the
            # exact commit of this repository it names. Published so a reader can check
            # the run against the tree rather than take the summary on trust.
            @{ From = "projects\chia-cfmm\docs\FORGE_AUDIT_RUN_V14_2026-09-19.md"; To = "docs\FORGE_AUDIT_RUN_V14_2026-09-19.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.SECURITY.md"; To = "docs\FORGE_SECURITY.md" }
            # The audit runbook travels with the puzzles it audits: the method that
            # finds defects in this code should be as public as the code, and as open
            # to correction. A directory rather than a file, so a model that discovers
            # skills by convention finds it and a contributor can add one beside it.
            @{ From = "projects\chia-cfmm\skills"; To = "skills" }
            @{ From = "projects\chia-cfmm\docs\chip";  To = "docs\chip" }
            # FORGE_SECURITY.md and the CHIP's Test Cases section both cite this
            # by path; it ships so those references resolve.
            @{ From = "projects\chia-cfmm\scripts\mutate-v14.py"; To = "scripts\mutate-v14.py" }
            @{ From = "projects\chia-cfmm\scripts\build-v14.py";  To = "scripts\build-v14.py" }
            # The evidence the V14 documents cite. A citation that resolves for us and points
            # at nothing for an external reader is the failure the fifth review named, and
            # scripts/check-doc-links.py fails the build on it. These carry no exploit against
            # a live revision: they are our own probes against our own current puzzles, and a
            # reviewer cannot check "the node refuses this" without them.
            @{ From = "projects\chia-cfmm\scripts\sim-v14.py";              To = "scripts\sim-v14.py" }
            @{ From = "projects\chia-cfmm\scripts\sim-v14-batch-security.py"; To = "scripts\sim-v14-batch-security.py" }
            @{ From = "projects\chia-cfmm\scripts\v14-squat-probe.py";      To = "scripts\v14-squat-probe.py" }
            @{ From = "projects\chia-cfmm\scripts\v14-settlement-probe.py"; To = "scripts\v14-settlement-probe.py" }
            @{ From = "projects\chia-cfmm\scripts\v14-slack-probe.py";      To = "scripts\v14-slack-probe.py" }
            # v14-route-audit.py is NOT here. It quotes every route on the LIVE pool states
            # through our wallet driver, it is cited by no published document, and it could
            # not run in this repository. The three probes above stay because published
            # documents cite them as the record of what the node answered; each one now says
            # in its own header that it reads rather than runs here, and names what does run.
            # The probe that answers the automated review of CHIP-0062 revision 8 on an
            # in-process node. It is self-contained: it drives sim-v14.py and needs no wallet,
            # so a reader can run it. Its LIVE twin, v14-reserve-message-probe.py, is NOT here --
            # it drives our testnet wallet through deploy-v14-testnet.py, which stays private,
            # and a reader could not sign from our wallet anyway. Both build the same
            # construction; only one of them is runnable by someone else.
            @{ From = "projects\chia-cfmm\scripts\sim-v14-review-derivations.py"; To = "scripts\sim-v14-review-derivations.py" }
            # The CHIP-0062 audit findings a node has to judge (M-2 ephemeral chaining, C-1 two
            # eves, M-3 squat, L-6 slot), against V14 only, on a simulator. Published so the
            # 2026-09-19 audit run is reproducible from this tree.
            @{ From = "projects\chia-cfmm\scripts\sim-v14-chip0062.py"; To = "scripts\sim-v14-chip0062.py" }
            @{ From = "projects\chia-cfmm\scripts\check-doc-links.py";      To = "scripts\check-doc-links.py" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.gitignore"; To = ".gitignore" }
            # Line endings are pinned because the manifest hashes puzzle sources for
            # provenance. Without it a Windows checkout rewrites them and 11 of 41 source
            # hashes stop matching the blob, which is exactly what the fourth review hit.
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-puzzles.gitattributes"; To = ".gitattributes" }
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
            # ── the responder half ───────────────────────────────────────────────
            #
            # Vercel serves the UI from this repo and Railway runs the responder from
            # the same commit, so both halves have to be here. .vercelignore keeps
            # everything below out of the Vercel upload; nixpacks builds all of it.
            #
            # contracts/ is the whole reason this cannot be a serverless deploy: every
            # settling route shells out to Python in it. Only the shipping revision
            # travels -- the 46 modules the responder imports, plus contracts/v14 and
            # contracts/compiled. The suites, the simulators and every retired revision
            # are maintained in the monorepo and audited from forge-puzzles.
            @{ From = "projects\chia-cfmm\contracts"; To = "contracts"
               Except      = $ForgeUiPrune.excludeDirs
               ExceptFiles = $ForgeUiPrune.excludeFiles }
            @{ From = "projects\chia-cfmm\local-test-host.mjs"; To = "local-test-host.mjs" }
            @{ From = "projects\chia-cfmm\requirements.txt";    To = "requirements.txt" }
            # A Dockerfile rather than a builder's guess: Node and Python together
            # defeat language detection, and the builder that handled both is
            # deprecated. See docs/FORGE_HOSTING_SPLIT.md.
            @{ From = "projects\chia-cfmm\Dockerfile";    To = "Dockerfile" }
            @{ From = "projects\chia-cfmm\railpack.json";  To = "railpack.json" }
            @{ From = "projects\chia-cfmm\.dockerignore"; To = ".dockerignore" }
            # Named one file at a time on purpose: .awizard\ is in $AlwaysExclude
            # because it is live state and the place a key would end up. These three
            # hold none -- pool records, lock records, and registry slot ids, all of
            # which the responder already serves publicly -- and without them a fresh
            # container comes up with no pools at all. The host copies them into
            # AWIZARD_STATE_DIR once, only where that file does not exist yet.
            @{ From = "projects\chia-cfmm\.awizard\deployment-index.json"; To = "data\state-seed\deployment-index.json" }
            @{ From = "projects\chia-cfmm\.awizard\multisig-index.json";   To = "data\state-seed\multisig-index.json" }
            @{ From = "projects\chia-cfmm\.awizard\v14-testnet.json";      To = "data\state-seed\v14-testnet.json" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.vercelignore"; To = ".vercelignore" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.npmrc"; To = ".npmrc" }
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
            # How the UI half here is hosted apart from the responder half, which
            # lives in the Forge repo because this slice carries no contracts.
            @{ From = "projects\chia-cfmm\docs\FORGE_HOSTING_SPLIT.md"; To = "docs\FORGE_HOSTING_SPLIT.md" }
            @{ From = "projects\chia-cfmm\docs\FORGE_REVISION_UPGRADE.md"; To = "docs\FORGE_REVISION_UPGRADE.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.README.md"; To = "README.md" }
            @{ From = "projects\chia-cfmm\docs\subrepo\forge-ui.env.example"; To = ".env.example" }
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

    # /PURGE removes what the source no longer has; it does NOT remove what an
    # exclusion skipped, because robocopy never looks inside an excluded path.
    # So a pattern added today leaves yesterday's copies sitting in the sub-repo
    # -- which is how a repo that is meant to carry one revision keeps shipping
    # three. Exclusions have to be authoritative, so they are applied to the
    # destination too.
    # Only the slice's OWN exclusions are enforced here. $AlwaysExclude covers
    # node_modules, dist and .awizard -- the destination's local working state,
    # which this script has no business deleting. "Never copy this" and "this
    # must not exist there" are different statements.
    foreach ($dir in @($Slice.Except | Where-Object { $_ })) {
        Get-ChildItem -Path $target -Directory -Recurse -Force -Filter $dir -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($Detailed) { Write-Status "    prune dir  $($_.FullName.Substring($target.Length + 1))" "DarkYellow" }
                Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
            }
    }
    foreach ($pattern in @($Slice.ExceptFiles | Where-Object { $_ })) {
        Get-ChildItem -Path $target -File -Recurse -Force -Filter $pattern -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($Detailed) { Write-Status "    prune file $($_.FullName.Substring($target.Length + 1))" "DarkYellow" }
                Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue
            }
    }
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
