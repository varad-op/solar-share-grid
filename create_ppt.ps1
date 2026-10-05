Add-Type -AssemblyName System.Drawing

function Color-To-Ole([int]$r, [int]$g, [int]$b) {
    return [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb($r, $g, $b))
}

$bullet = [char]0x2022 + " "

$navyBg     = Color-To-Ole 11 17 32      # #0B1120
$cardBg     = Color-To-Ole 26 38 57      # #1A2639
$cardBorder = Color-To-Ole 45 62 80      # #2D3E50
$gold       = Color-To-Ole 245 158 11    # #F59E0B
$emerald    = Color-To-Ole 16 185 129    # #10B981
$white      = Color-To-Ole 255 255 255  # #FFFFFF
$slateText  = Color-To-Ole 148 163 184  # #94A3B8
$lightCard  = Color-To-Ole 18 27 43      # #121B2B

$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Add([Microsoft.Office.Core.MsoTriState]::msoFalse)
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540

# ==============================================================
# --- SLIDE 1: Title Slide ---
# ==============================================================
$s1 = $pres.Slides.Add(1, 12) # ppLayoutBlank

# Background
$bg1 = $s1.Shapes.AddShape(1, 0, 0, 960, 540)
$bg1.Fill.Solid()
$bg1.Fill.ForeColor.RGB = $navyBg
$bg1.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Top decorative accent line
$topLine = $s1.Shapes.AddShape(1, 0, 0, 960, 6)
$topLine.Fill.Solid()
$topLine.Fill.ForeColor.RGB = $gold
$topLine.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Badge / Category
$badge1 = $s1.Shapes.AddShape(5, 80, 65, 300, 30) # rounded rect
$badge1.Fill.Solid()
$badge1.Fill.ForeColor.RGB = $cardBg
$badge1.Line.ForeColor.RGB = $gold
$badge1.Line.Weight = 1.5
$badge1.TextFrame.TextRange.Text = "DISCRETE MATHEMATICS & GRAPH THEORY"
$badge1.TextFrame.TextRange.Font.Name = "Segoe UI"
$badge1.TextFrame.TextRange.Font.Size = 10
$badge1.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$badge1.TextFrame.TextRange.Font.Color.RGB = $gold
$badge1.TextFrame.TextRange.ParagraphFormat.Alignment = 2 # Center

# Title: Solar Share Grid
$titleBox = $s1.Shapes.AddTextbox(1, 80, 110, 800, 75)
$titleBox.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$titleBox.TextFrame.TextRange.Text = "Solar Share Grid"
$titleBox.TextFrame.TextRange.Font.Name = "Segoe UI"
$titleBox.TextFrame.TextRange.Font.Size = 50
$titleBox.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$titleBox.TextFrame.TextRange.Font.Color.RGB = $white

# Subtitle
$subBox = $s1.Shapes.AddTextbox(1, 80, 195, 800, 55)
$subBox.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$subBox.TextFrame.TextRange.Text = "A Peer-to-Peer Rooftop Solar Trading Microgrid Simulator Powered by Binary Relations, Warshall's Transitive Closure, and Heuristic Graph Optimization"
$subBox.TextFrame.TextRange.Font.Name = "Segoe UI"
$subBox.TextFrame.TextRange.Font.Size = 14
$subBox.TextFrame.TextRange.Font.Color.RGB = $slateText

# Student Info Card (Slide 1)
$card1 = $s1.Shapes.AddShape(5, 80, 280, 530, 195)
$card1.Fill.Solid()
$card1.Fill.ForeColor.RGB = $cardBg
$card1.Line.ForeColor.RGB = $cardBorder
$card1.Line.Weight = 1.5

# Student Info Header inside card
$sih = $s1.Shapes.AddTextbox(1, 105, 295, 480, 28)
$sih.TextFrame.TextRange.Text = "PROJECT AUTHOR & DETAILS"
$sih.TextFrame.TextRange.Font.Name = "Segoe UI"
$sih.TextFrame.TextRange.Font.Size = 11
$sih.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$sih.TextFrame.TextRange.Font.Color.RGB = $emerald

# Student Name
$sn = $s1.Shapes.AddTextbox(1, 105, 325, 480, 42)
$sn.TextFrame.TextRange.Text = "Name: Varad Bele"
$sn.TextFrame.TextRange.Font.Name = "Segoe UI"
$sn.TextFrame.TextRange.Font.Size = 24
$sn.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$sn.TextFrame.TextRange.Font.Color.RGB = $white

# Student Roll No
$sr = $s1.Shapes.AddTextbox(1, 105, 375, 480, 36)
$sr.TextFrame.TextRange.Text = "Roll No: 16015025004"
$sr.TextFrame.TextRange.Font.Name = "Segoe UI"
$sr.TextFrame.TextRange.Font.Size = 20
$sr.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$sr.TextFrame.TextRange.Font.Color.RGB = $gold

# Academic details
$sa = $s1.Shapes.AddTextbox(1, 105, 425, 480, 30)
$sa.TextFrame.TextRange.Text = "B.Tech Second Year | Computer Engineering | Discrete Mathematics"
$sa.TextFrame.TextRange.Font.Name = "Segoe UI"
$sa.TextFrame.TextRange.Font.Size = 13
$sa.TextFrame.TextRange.Font.Color.RGB = $slateText

# Right Stats Card on Slide 1
$statCard = $s1.Shapes.AddShape(5, 640, 280, 240, 195)
$statCard.Fill.Solid()
$statCard.Fill.ForeColor.RGB = $lightCard
$statCard.Line.ForeColor.RGB = $cardBorder
$statCard.Line.Weight = 1.5

$scHeader = $s1.Shapes.AddTextbox(1, 655, 295, 210, 28)
$scHeader.TextFrame.TextRange.Text = "SYSTEM ARCHITECTURE"
$scHeader.TextFrame.TextRange.Font.Name = "Segoe UI"
$scHeader.TextFrame.TextRange.Font.Size = 11
$scHeader.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$scHeader.TextFrame.TextRange.Font.Color.RGB = $gold

$scText = $s1.Shapes.AddTextbox(1, 655, 325, 215, 140)
$scText.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$scText.TextFrame.TextRange.Text = "$bullet 5 Core Math Engines`n$bullet Warshall's Algorithm O(V`^3)`n$bullet Equivalence Classes & SCCs`n$bullet Heuristic Line Optimizer`n$bullet Real P2P Trade Simulation"
$scText.TextFrame.TextRange.Font.Name = "Segoe UI"
$scText.TextFrame.TextRange.Font.Size = 12
$scText.TextFrame.TextRange.Font.Color.RGB = $slateText

# ==============================================================
# --- SLIDE 2: Problem Statement ---
# ==============================================================
$s2 = $pres.Slides.Add(2, 12)

# Background
$bg2 = $s2.Shapes.AddShape(1, 0, 0, 960, 540)
$bg2.Fill.Solid()
$bg2.Fill.ForeColor.RGB = $navyBg
$bg2.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Top line
$topLine2 = $s2.Shapes.AddShape(1, 0, 0, 960, 6)
$topLine2.Fill.Solid()
$topLine2.Fill.ForeColor.RGB = $gold
$topLine2.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Header Badge
$b2 = $s2.Shapes.AddShape(5, 60, 30, 180, 26)
$b2.Fill.Solid()
$b2.Fill.ForeColor.RGB = $cardBg
$b2.Line.ForeColor.RGB = $gold
$b2.Line.Weight = 1.2
$b2.TextFrame.TextRange.Text = "PROBLEM STATEMENT"
$b2.TextFrame.TextRange.Font.Name = "Segoe UI"
$b2.TextFrame.TextRange.Font.Size = 10
$b2.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$b2.TextFrame.TextRange.Font.Color.RGB = $gold
$b2.TextFrame.TextRange.ParagraphFormat.Alignment = 2

# Slide 2 Title
$s2Title = $s2.Shapes.AddTextbox(1, 60, 60, 840, 42)
$s2Title.TextFrame.TextRange.Text = "The Challenge in Decentralized Rooftop Solar Distribution"
$s2Title.TextFrame.TextRange.Font.Name = "Segoe UI"
$s2Title.TextFrame.TextRange.Font.Size = 25
$s2Title.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$s2Title.TextFrame.TextRange.Font.Color.RGB = $white

# 4 Problem Cards (2x2 Grid)
# Card 1: Solar Surplus Mismatch
$c1 = $s2.Shapes.AddShape(5, 60, 115, 410, 160)
$c1.Fill.Solid()
$c1.Fill.ForeColor.RGB = $cardBg
$c1.Line.ForeColor.RGB = $cardBorder
$c1.Line.Weight = 1.2

$c1H = $s2.Shapes.AddTextbox(1, 75, 125, 380, 28)
$c1H.TextFrame.TextRange.Text = "1. Solar Generation & Demand Mismatch"
$c1H.TextFrame.TextRange.Font.Name = "Segoe UI"
$c1H.TextFrame.TextRange.Font.Size = 13.5
$c1H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c1H.TextFrame.TextRange.Font.Color.RGB = $gold

$c1B = $s2.Shapes.AddTextbox(1, 75, 155, 380, 110)
$c1B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c1B.TextFrame.TextRange.Text = "$bullet Solar-equipped homes produce excess power during peak daylight hours when household consumption is low.`n$bullet Non-solar neighbors suffer power deficits or expensive utility tariffs without an equitable local sharing grid."
$c1B.TextFrame.TextRange.Font.Name = "Segoe UI"
$c1B.TextFrame.TextRange.Font.Size = 11.5
$c1B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Card 2: Directional Physical Constraints
$c2 = $s2.Shapes.AddShape(5, 490, 115, 410, 160)
$c2.Fill.Solid()
$c2.Fill.ForeColor.RGB = $cardBg
$c2.Line.ForeColor.RGB = $cardBorder
$c2.Line.Weight = 1.2

$c2H = $s2.Shapes.AddTextbox(1, 505, 125, 380, 28)
$c2H.TextFrame.TextRange.Text = "2. Directional Grid Constraints (Digraphs)"
$c2H.TextFrame.TextRange.Font.Name = "Segoe UI"
$c2H.TextFrame.TextRange.Font.Size = 13.5
$c2H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c2H.TextFrame.TextRange.Font.Color.RGB = $gold

$c2B = $s2.Shapes.AddTextbox(1, 505, 155, 380, 110)
$c2B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c2B.TextFrame.TextRange.Text = "$bullet Power lines operate under asymmetric or unidirectional power converters and feed-in safety limits.`n$bullet Geographical proximity does NOT imply electrical reachability; valid directed transmission paths must exist."
$c2B.TextFrame.TextRange.Font.Name = "Segoe UI"
$c2B.TextFrame.TextRange.Font.Size = 11.5
$c2B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Card 3: The Left-Out Household Problem
$c3 = $s2.Shapes.AddShape(5, 60, 290, 410, 160)
$c3.Fill.Solid()
$c3.Fill.ForeColor.RGB = $cardBg
$c3.Line.ForeColor.RGB = $cardBorder
$c3.Line.Weight = 1.2

$c3H = $s2.Shapes.AddTextbox(1, 75, 300, 380, 28)
$c3H.TextFrame.TextRange.Text = "3. The 'Left-Out Household' Crisis"
$c3H.TextFrame.TextRange.Font.Name = "Segoe UI"
$c3H.TextFrame.TextRange.Font.Size = 13.5
$c3H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c3H.TextFrame.TextRange.Font.Color.RGB = Color-To-Ole 248 113 113 # Soft Red #F87171

$c3B = $s2.Shapes.AddTextbox(1, 75, 330, 380, 110)
$c3B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c3B.TextFrame.TextRange.Text = "$bullet Consumer homes with real energy demand remain isolated with zero access to upstream solar producers.`n$bullet Formally: Reach^-1(v) contains NO surplus node. These homes receive 0 kW clean energy despite neighborhood surplus."
$c3B.TextFrame.TextRange.Font.Name = "Segoe UI"
$c3B.TextFrame.TextRange.Font.Size = 11.5
$c3B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Card 4: Multi-Hop Loss & Inefficient Cabling
$c4 = $s2.Shapes.AddShape(5, 490, 290, 410, 160)
$c4.Fill.Solid()
$c4.Fill.ForeColor.RGB = $cardBg
$c4.Line.ForeColor.RGB = $cardBorder
$c4.Line.Weight = 1.2

$c4H = $s2.Shapes.AddTextbox(1, 505, 300, 380, 28)
$c4H.TextFrame.TextRange.Text = "4. Transmission Loss & Arbitrary Cabling"
$c4H.TextFrame.TextRange.Font.Name = "Segoe UI"
$c4H.TextFrame.TextRange.Font.Size = 13.5
$c4H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c4H.TextFrame.TextRange.Font.Color.RGB = $gold

$c4B = $s2.Shapes.AddTextbox(1, 505, 330, 380, 110)
$c4B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$c4B.TextFrame.TextRange.Text = "$bullet Multi-hop line resistance causes cumulative power loss: Delivered = Surplus x Product(1 - loss_i).`n$bullet Microgrid engineers lack algorithmic tools to select the optimal missing link to install that maximizes coverage."
$c4B.TextFrame.TextRange.Font.Name = "Segoe UI"
$c4B.TextFrame.TextRange.Font.Size = 11.5
$c4B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Bottom Callout Banner
$botBanner = $s2.Shapes.AddShape(5, 60, 465, 840, 50)
$botBanner.Fill.Solid()
$botBanner.Fill.ForeColor.RGB = $lightCard
$botBanner.Line.ForeColor.RGB = $emerald
$botBanner.Line.Weight = 1.2

$bbText = $s2.Shapes.AddTextbox(1, 75, 472, 810, 36)
$bbText.TextFrame.TextRange.Text = "PROJECT MISSION: Use Discrete Mathematics (Binary Relations, Warshall's Algorithm, SCCs) to transform chaotic physical microgrids into self-healing, equitable, and zero-loss P2P energy networks."
$bbText.TextFrame.TextRange.Font.Name = "Segoe UI"
$bbText.TextFrame.TextRange.Font.Size = 11
$bbText.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$bbText.TextFrame.TextRange.Font.Color.RGB = $emerald

# ==============================================================
# --- SLIDE 3: Features Overview ---
# ==============================================================
$s3 = $pres.Slides.Add(3, 12)

# Background
$bg3 = $s3.Shapes.AddShape(1, 0, 0, 960, 540)
$bg3.Fill.Solid()
$bg3.Fill.ForeColor.RGB = $navyBg
$bg3.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Top line
$topLine3 = $s3.Shapes.AddShape(1, 0, 0, 960, 6)
$topLine3.Fill.Solid()
$topLine3.Fill.ForeColor.RGB = $emerald
$topLine3.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse

# Header Badge
$b3 = $s3.Shapes.AddShape(5, 60, 25, 200, 26)
$b3.Fill.Solid()
$b3.Fill.ForeColor.RGB = $cardBg
$b3.Line.ForeColor.RGB = $emerald
$b3.Line.Weight = 1.2
$b3.TextFrame.TextRange.Text = "FEATURES OVERVIEW"
$b3.TextFrame.TextRange.Font.Name = "Segoe UI"
$b3.TextFrame.TextRange.Font.Size = 10
$b3.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$b3.TextFrame.TextRange.Font.Color.RGB = $emerald
$b3.TextFrame.TextRange.ParagraphFormat.Alignment = 2

# Slide 3 Title
$s3Title = $s3.Shapes.AddTextbox(1, 60, 54, 840, 38)
$s3Title.TextFrame.TextRange.Text = "Key Features of the Solar Share Grid Platform"
$s3Title.TextFrame.TextRange.Font.Name = "Segoe UI"
$s3Title.TextFrame.TextRange.Font.Size = 25
$s3Title.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$s3Title.TextFrame.TextRange.Font.Color.RGB = $white

# 5 Feature Cards across layout
# F1: Transitive Closure Engine
$f1 = $s3.Shapes.AddShape(5, 60, 98, 410, 130)
$f1.Fill.Solid()
$f1.Fill.ForeColor.RGB = $cardBg
$f1.Line.ForeColor.RGB = $cardBorder
$f1.Line.Weight = 1.2

$f1H = $s3.Shapes.AddTextbox(1, 75, 105, 380, 26)
$f1H.TextFrame.TextRange.Text = "1. Warshall's Transitive Closure Engine"
$f1H.TextFrame.TextRange.Font.Name = "Segoe UI"
$f1H.TextFrame.TextRange.Font.Size = 13
$f1H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f1H.TextFrame.TextRange.Font.Color.RGB = $emerald

$f1B = $s3.Shapes.AddTextbox(1, 75, 132, 380, 88)
$f1B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f1B.TextFrame.TextRange.Text = "$bullet Custom O(V`^3) Warshall's algorithm computed step-by-step from scratch.`n$bullet Computes all indirect, multi-hop power pathways (R`^+).`n$bullet Mathematical relation analyzer: Reflexive, Symmetric, and Transitive closures."
$f1B.TextFrame.TextRange.Font.Name = "Segoe UI"
$f1B.TextFrame.TextRange.Font.Size = 11
$f1B.TextFrame.TextRange.Font.Color.RGB = $slateText

# F2: Reachability & Left-Out Audit
$f2 = $s3.Shapes.AddShape(5, 60, 238, 410, 130)
$f2.Fill.Solid()
$f2.Fill.ForeColor.RGB = $cardBg
$f2.Line.ForeColor.RGB = $cardBorder
$f2.Line.Weight = 1.2

$f2H = $s3.Shapes.AddTextbox(1, 75, 245, 380, 26)
$f2H.TextFrame.TextRange.Text = "2. Reachability & Left-Out Household Detection"
$f2H.TextFrame.TextRange.Font.Name = "Segoe UI"
$f2H.TextFrame.TextRange.Font.Size = 13
$f2H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f2H.TextFrame.TextRange.Font.Color.RGB = $emerald

$f2B = $s3.Shapes.AddTextbox(1, 75, 272, 380, 88)
$f2B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f2B.TextFrame.TextRange.Text = "$bullet Computes exact Reachability Sets Reach(v) for each solar producer.`n$bullet Automated audit flags stranded consumer homes with zero upstream solar.`n$bullet Live KPI metrics: Solar Self-Sufficiency Index (%) & Household Isolation Rate (%)."
$f2B.TextFrame.TextRange.Font.Name = "Segoe UI"
$f2B.TextFrame.TextRange.Font.Size = 11
$f2B.TextFrame.TextRange.Font.Color.RGB = $slateText

# F3: Equivalence & Energy Communities
$f3 = $s3.Shapes.AddShape(5, 490, 98, 410, 130)
$f3.Fill.Solid()
$f3.Fill.ForeColor.RGB = $cardBg
$f3.Line.ForeColor.RGB = $cardBorder
$f3.Line.Weight = 1.2

$f3H = $s3.Shapes.AddTextbox(1, 505, 105, 380, 26)
$f3H.TextFrame.TextRange.Text = "3. Strongly Connected Energy Communities"
$f3H.TextFrame.TextRange.Font.Name = "Segoe UI"
$f3H.TextFrame.TextRange.Font.Size = 13
$f3H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f3H.TextFrame.TextRange.Font.Color.RGB = $gold

$f3B = $s3.Shapes.AddTextbox(1, 505, 132, 380, 88)
$f3B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f3B.TextFrame.TextRange.Text = "$bullet Decomposes the microgrid into Strongly Connected Components (SCCs).`n$bullet Proves mutual energy exchange: u can supply v and v can supply u.`n$bullet Equivalence classes form resilient micro-islands capable of autonomous operation."
$f3B.TextFrame.TextRange.Font.Name = "Segoe UI"
$f3B.TextFrame.TextRange.Font.Size = 11
$f3B.TextFrame.TextRange.Font.Color.RGB = $slateText

# F4: Missing Link AI Optimizer
$f4 = $s3.Shapes.AddShape(5, 490, 238, 410, 130)
$f4.Fill.Solid()
$f4.Fill.ForeColor.RGB = $cardBg
$f4.Line.ForeColor.RGB = $cardBorder
$f4.Line.Weight = 1.2

$f4H = $s3.Shapes.AddTextbox(1, 505, 245, 380, 26)
$f4H.TextFrame.TextRange.Text = "4. Graph AI Missing Link Optimizer"
$f4H.TextFrame.TextRange.Font.Name = "Segoe UI"
$f4H.TextFrame.TextRange.Font.Size = 13
$f4H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f4H.TextFrame.TextRange.Font.Color.RGB = $gold

$f4B = $s3.Shapes.AddTextbox(1, 505, 272, 380, 88)
$f4B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f4B.TextFrame.TextRange.Text = "$bullet Evaluates all possible missing directed lines (u, v) not yet in the grid.`n$bullet Efficiency Score = (Delta Powered Homes x Newly Served kW) / Euclidean Distance.`n$bullet Recommends the SINGLE optimal power line to eliminate left-out homes at lowest cost."
$f4B.TextFrame.TextRange.Font.Name = "Segoe UI"
$f4B.TextFrame.TextRange.Font.Size = 11
$f4B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Bottom Wide Card (F5: Trade Simulator & Export)
$f5 = $s3.Shapes.AddShape(5, 60, 380, 840, 135)
$f5.Fill.Solid()
$f5.Fill.ForeColor.RGB = $cardBg
$f5.Line.ForeColor.RGB = $cardBorder
$f5.Line.Weight = 1.2

$f5H = $s3.Shapes.AddTextbox(1, 75, 388, 810, 26)
$f5H.TextFrame.TextRange.Text = "5. Physics-Based P2P Trade Settlement & Executive Export"
$f5H.TextFrame.TextRange.Font.Name = "Segoe UI"
$f5H.TextFrame.TextRange.Font.Size = 13
$f5H.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f5H.TextFrame.TextRange.Font.Color.RGB = Color-To-Ole 56 189 248 # Sky Blue #38BDF8

$f5B = $s3.Shapes.AddTextbox(1, 75, 414, 810, 92)
$f5B.TextFrame.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$f5B.TextFrame.TextRange.Text = "$bullet Multi-hop transmission loss model: Delivered Power = Surplus x Product(1 - loss_i) for k hops.`n$bullet Greedy shortest-distance P2P settlement ledger calculating sent kW, line losses, and financial bill savings.`n$bullet 1-Click Executive Summary Report export (CSV/PDF) containing microgrid KPIs and transaction records.`n$bullet 4 Pre-built realistic microgrid presets localized to Nerul, Navi Mumbai (Suburban, Hillside, Islands, Custom)."
$f5B.TextFrame.TextRange.Font.Name = "Segoe UI"
$f5B.TextFrame.TextRange.Font.Size = 11
$f5B.TextFrame.TextRange.Font.Color.RGB = $slateText

# Save presentation to workspace
$outPptx = "D:\DM maths Final\Solar_Share_Grid_Presentation.pptx"
$pres.SaveAs($outPptx)

# Export slides to images for instant chat preview
$outDir = "C:\Users\varadbele\.gemini\antigravity\brain\621e7364-8f8d-49fd-8de8-7bf5e38b274c"
$s1.Export((Join-Path $outDir "slide_1.png"), "PNG", 1920, 1080)
$s2.Export((Join-Path $outDir "slide_2.png"), "PNG", 1920, 1080)
$s3.Export((Join-Path $outDir "slide_3.png"), "PNG", 1920, 1080)

$pres.Close()
$ppt.Quit()

Write-Output "Refined PPTX created successfully at: $outPptx"
