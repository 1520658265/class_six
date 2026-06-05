# 批量生成 hero01 的头像和表情差分
# 用法: .\batch_generate_faces.ps1

$ErrorActionPreference = "Stop"
$BASE = "D:\PersonalProject\class_six\tools\ai"
$REF = "D:\证件照片\1.jpg"
$PROMPT_DIR = "$BASE\out\hero01\prompts"
$OUT_DIR = "$BASE\out\hero01"

# 表情列表：名称 -> 表情描述
$expressions = @{
    "happy" = "smiling brightly, eyes squinted with joy, open mouth smile, cheerful"
    "angry" = "furrowed brows, gritted teeth, intense eyes, flushed cheeks, annoyed expression"
    "sad" = "downcast eyes, slight frown, melancholy, tears welling up, dejected"
    "surprised" = "wide eyes, raised eyebrows, open mouth, shocked expression"
    "shy" = "blushing cheeks, looking away slightly, small embarrassed smile, timid"
    "hurt" = "pained expression, wincing, one eye closed, grimacing"
}

Write-Host "[INFO] 开始批量生成..." -ForegroundColor Cyan

# 1. 生成头像（neutral 表情）
Write-Host "`n[1/7] 生成头像（neutral）..." -ForegroundColor Yellow
python gen_with_gemini.py "$PROMPT_DIR\face-icon-neutral.txt" --aspect 1:1 --size 1K --ref $REF -o "$OUT_DIR\face-neutral"
if ($LASTEXITCODE -eq 0) {
    python jpg_to_png_alpha.py "$OUT_DIR\face-neutral.jpg" -o "$OUT_DIR\face-neutral.png"
    Write-Host "[OK] face-neutral.png" -ForegroundColor Green
}

# 2. 生成 6 个表情差分
$i = 2
foreach ($expr in $expressions.GetEnumerator()) {
    $name = $expr.Key
    $desc = $expr.Value

    Write-Host "`n[$i/7] 生成表情: $name..." -ForegroundColor Yellow

    # 读取 neutral prompt 模板
    $template = Get-Content "$PROMPT_DIR\face-icon-neutral.txt" -Raw -Encoding UTF8

    # 替换表情描述
    $prompt = $template -replace "Expression: NEUTRAL / CALM \(default resting face, slight hint of trying to look cool\)", "Expression: $desc"

    # 保存临时 prompt
    $tempPrompt = "$PROMPT_DIR\face-icon-$name.txt"
    [System.IO.File]::WriteAllText($tempPrompt, $prompt, [System.Text.UTF8Encoding]::new($false))

    # 生成图片
    python gen_with_gemini.py $tempPrompt --aspect 1:1 --size 1K --ref $REF -o "$OUT_DIR\face-$name"

    if ($LASTEXITCODE -eq 0) {
        # 抠图
        python jpg_to_png_alpha.py "$OUT_DIR\face-$name.jpg" -o "$OUT_DIR\face-$name.png"
        Write-Host "[OK] face-$name.png" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] face-$name" -ForegroundColor Red
    }

    $i++
}

Write-Host "`n[完成] 共生成 7 张图片（1 头像 + 6 表情）" -ForegroundColor Cyan
Write-Host "输出目录: $OUT_DIR" -ForegroundColor Cyan
