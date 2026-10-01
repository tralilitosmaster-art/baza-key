--[[
    Baza.Key Loader v1.2.0
    LootLabs + Flask Backend + Discord
--]]

if _G.BAZA_LOADER_LOADED then return end
_G.BAZA_LOADER_LOADED = true

local CONFIG = {
    Version = "1.2.0",
    MainURL = "https://raw.githubusercontent.com/tralilitosmaster-art/BazCrackLua-/main/main.lua",
    OldURL  = "https://raw.githubusercontent.com/tralilitosmaster-art/BazCrackLua-/main/main.lua",
    ApiUrl  = "https://baza-key.onrender.com",
    Discord = "https://discord.gg/vVFeyntpa",
    Webhook = "YOUR_DISCORD_WEBHOOK_URL", -- для логов
}

local COLORS = {
    Black     = Color3.fromRGB(0, 0, 0),
    DeepRed   = Color3.fromRGB(60, 0, 0),
    DarkRed   = Color3.fromRGB(100, 0, 0),
    Red       = Color3.fromRGB(180, 0, 0),
    BrightRed = Color3.fromRGB(255, 40, 40),
    Text      = Color3.fromRGB(255, 255, 255),
    SubText   = Color3.fromRGB(200, 150, 150),
    Green     = Color3.fromRGB(40, 220, 100),
    Yellow    = Color3.fromRGB(255, 210, 60),
    DiscordPurple = Color3.fromRGB(88, 101, 242),
    DiscordLight  = Color3.fromRGB(114, 137, 218),
}

local Players = game:GetService("Players")
local LP = Players.LocalPlayer

local function Gradient(obj, c1, c2, rot)
    local g = Instance.new("UIGradient")
    g.Color = ColorSequence.new(c1, c2)
    g.Rotation = rot or 45
    g.Parent = obj
    return g
end
local function Corner(obj, r)
    local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, r or 6); c.Parent = obj; return c
end
local function Stroke(obj, color, th)
    local s = Instance.new("UIStroke"); s.Color = color or COLORS.BrightRed; s.Thickness = th or 1.5; s.Parent = obj; return s
end
local function Pad(obj, p)
    local pad = Instance.new("UIPadding")
    pad.PaddingTop = UDim.new(0, p); pad.PaddingBottom = UDim.new(0, p)
    pad.PaddingLeft = UDim.new(0, p); pad.PaddingRight = UDim.new(0, p)
    pad.Parent = obj
    return pad
end

local function GetHWID()
    local ok, hwid = pcall(function()
        return game:GetService("RbxAnalyticsService"):GetClientId()
    end)
    if ok and hwid then return hwid end
    local uid = tostring(LP and LP.UserId or 0)
    local hash = 0
    for i = 1, #uid do hash = (hash * 31 + uid:byte(i)) % 2^31 end
    return "BCL_" .. tostring(hash)
end

local function LogToDiscord(msg)
    if not CONFIG.Webhook or CONFIG.Webhook == "YOUR_DISCORD_WEBHOOK_URL" then return end
    local HttpService = game:GetService("HttpService")
    local payload = HttpService:JSONEncode({
        username = "Baza.Key Logger",
        content = msg
    })
    pcall(function()
        if type(request) == "function" then
            request({Url = CONFIG.Webhook, Method = "POST",
                Headers = {["Content-Type"] = "application/json"},
                Body = payload})
        elseif type(game.HttpPost) == "function" then
            game:HttpPost(CONFIG.Webhook, payload, "ApplicationJson")
        end
    end)
end

local function ValidateKey(key, hwid)
    local HttpService = game:GetService("HttpService")
    local body = HttpService:JSONEncode({key = key, hwid = hwid})

    local ok, res
    if type(request) == "function" then
        ok, res = pcall(request, {
            Url = CONFIG.ApiUrl .. "/validate",
            Method = "POST",
            Headers = {["Content-Type"] = "application/json"},
            Body = body
        })
        if ok and type(res) == "table" and res.Body then res = res.Body end
    end
    if not ok or not res then
        if type(game.HttpPost) == "function" then
            ok, res = pcall(function()
                return game:HttpPost(CONFIG.ApiUrl .. "/validate", body, "ApplicationJson")
            end)
        end
    end
    if not ok or not res then return false, "api_error" end

    local data = HttpService:JSONDecode(res)
    if data.valid then return true, data end
    return false, data.reason or "unknown"
end

local ScreenGui = Instance.new("ScreenGui")
ScreenGui.Name = "BazaKey_Loader"
ScreenGui.ResetOnSpawn = false
ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
ScreenGui.DisplayOrder = 10000
pcall(function() ScreenGui.Parent = game:GetService("CoreGui") end)
if not ScreenGui.Parent then ScreenGui.Parent = LP:WaitForChild("PlayerGui") end

local Main = Instance.new("Frame")
Main.Size = UDim2.new(0, 480, 0, 340)
Main.Position = UDim2.new(0.5, -240, 0.5, -170)
Main.BackgroundColor3 = COLORS.Black
Main.BorderSizePixel = 0
Main.Parent = ScreenGui
Gradient(Main, COLORS.Black, COLORS.DeepRed, 135)
Corner(Main, 10)
local mainStroke = Stroke(Main, COLORS.BrightRed, 1.5)
Main.Active = true
Main.Draggable = true

local Title = Instance.new("TextLabel")
Title.Size = UDim2.new(1, 0, 0, 40)
Title.BackgroundColor3 = COLORS.DeepRed
Title.BorderSizePixel = 0
Title.Text = "  Baza.Key Loader v" .. CONFIG.Version
Title.TextColor3 = COLORS.Text
Title.Font = Enum.Font.GothamBold
Title.TextSize = 16
Title.TextXAlignment = Enum.TextXAlignment.Left
Title.Parent = Main
Gradient(Title, COLORS.DarkRed, COLORS.BrightRed, 0)

local HWIDLabel = Instance.new("TextLabel")
HWIDLabel.Size = UDim2.new(1, -20, 0, 20)
HWIDLabel.Position = UDim2.new(0, 10, 0, 48)
HWIDLabel.BackgroundTransparency = 1
HWIDLabel.Text = "HWID: " .. GetHWID():sub(1, 24) .. "..."
HWIDLabel.TextColor3 = COLORS.SubText
HWIDLabel.Font = Enum.Font.Code
HWIDLabel.TextSize = 11
HWIDLabel.TextXAlignment = Enum.TextXAlignment.Left
HWIDLabel.Parent = Main

local KeyInput = Instance.new("TextBox")
KeyInput.Size = UDim2.new(1, -20, 0, 42)
KeyInput.Position = UDim2.new(0, 10, 0, 74)
KeyInput.BackgroundColor3 = COLORS.Black
KeyInput.TextColor3 = COLORS.Text
KeyInput.PlaceholderText = "Enter Baza.Key (BAZA_BCL_xxx)..."
KeyInput.PlaceholderColor3 = COLORS.SubText
KeyInput.Font = Enum.Font.Code
KeyInput.TextSize = 14
KeyInput.ClearTextOnFocus = false
KeyInput.Parent = Main
Corner(KeyInput, 6); Stroke(KeyInput, COLORS.Red, 1); Pad(KeyInput, 6)

local Status = Instance.new("TextLabel")
Status.Size = UDim2.new(1, -20, 0, 20)
Status.Position = UDim2.new(0, 10, 0, 122)
Status.BackgroundTransparency = 1
Status.Text = "Ready."
Status.TextColor3 = COLORS.SubText
Status.Font = Enum.Font.Gotham
Status.TextSize = 12
Status.TextXAlignment = Enum.TextXAlignment.Left
Status.Parent = Main

local ActivateBtn = Instance.new("TextButton")
ActivateBtn.Size = UDim2.new(0, 220, 0, 40)
ActivateBtn.Position = UDim2.new(0, 10, 0, 152)
ActivateBtn.BackgroundColor3 = COLORS.Red
ActivateBtn.Text = "ACTIVATE"
ActivateBtn.TextColor3 = COLORS.Text
ActivateBtn.Font = Enum.Font.GothamBold
ActivateBtn.TextSize = 14
ActivateBtn.Parent = Main
Corner(ActivateBtn, 6)
Gradient(ActivateBtn, COLORS.DarkRed, COLORS.BrightRed, 0)

local OldBtn = Instance.new("TextButton")
OldBtn.Size = UDim2.new(0, 220, 0, 40)
OldBtn.Position = UDim2.new(0, 240, 0, 152)
OldBtn.BackgroundColor3 = COLORS.DeepRed
OldBtn.Text = "LOAD OLD (1.1)"
OldBtn.TextColor3 = COLORS.Text
OldBtn.Font = Enum.Font.GothamBold
OldBtn.TextSize = 13
OldBtn.Parent = Main
Corner(OldBtn, 6); Stroke(OldBtn, COLORS.Red, 1)

local DiscordBtn = Instance.new("TextButton")
DiscordBtn.Size = UDim2.new(1, -20, 0, 36)
DiscordBtn.Position = UDim2.new(0, 10, 1, -46)
DiscordBtn.BackgroundColor3 = COLORS.DiscordPurple
DiscordBtn.Text = "Get Key in Discord"
DiscordBtn.TextColor3 = COLORS.Text
DiscordBtn.Font = Enum.Font.GothamBold
DiscordBtn.TextSize = 13
DiscordBtn.Parent = Main
Corner(DiscordBtn, 6); Stroke(DiscordBtn, COLORS.DiscordLight, 1)
Gradient(DiscordBtn, COLORS.DiscordPurple, COLORS.DiscordLight, 45)

DiscordBtn.MouseButton1Click:Connect(function()
    if type(setclipboard) == "function" then pcall(setclipboard, CONFIG.Discord) end
    pcall(function() game:GetService("GuiService"):OpenBrowserWindow(CONFIG.Discord) end)
    Status.Text = "Discord link copied!"
    Status.TextColor3 = COLORS.DiscordLight
end)

local function RunMain(url)
    Status.Text = "Downloading..."
    Status.TextColor3 = COLORS.Yellow
    task.wait(0.2)
    local ok, src = pcall(function() return game:HttpGet(url .. "?t=" .. tick()) end)
    if ok and src and #src > 100 then
        Status.Text = "Executing BCL..."
        Status.TextColor3 = COLORS.Green
        task.wait(0.3)
        local execOk, err = pcall(function() loadstring(src)() end)
        if execOk then
            ScreenGui:Destroy()
            _G.BAZA_LOADER_LOADED = false
        else
            Status.Text = "Exec error: " .. tostring(err):sub(1, 60)
            Status.TextColor3 = COLORS.BrightRed
        end
    else
        Status.Text = "Download failed"
        Status.TextColor3 = COLORS.BrightRed
    end
end

ActivateBtn.MouseButton1Click:Connect(function()
    local key = KeyInput.Text
    if key == "" then
        Status.Text = "Enter a key."
        Status.TextColor3 = COLORS.BrightRed
        return
    end
    Status.Text = "Validating..."
    Status.TextColor3 = COLORS.Yellow
    task.wait(0.3)

    local hwid = GetHWID()
    local ok, data = ValidateKey(key, hwid)

    if ok then
        Status.Text = "Accepted. Plan: " .. (data.plan or "?"):upper() .. " | Tokens: " .. tostring(data.tokens_left or "?")
        Status.TextColor3 = COLORS.Green
        _G.BAZA_KEY = key
        _G.BAZA_PLAN = data.plan
        _G.BAZA_HWID = hwid
        _G.BAZA_TOKENS = data.tokens_left
        LogToDiscord(string.format("**Key Activated**\nKey: `%s`\nRoblox: `%s`\nHWID: `%s`\nPlan: `%s`",
            key, LP.Name, hwid:sub(1,16), data.plan))
        task.wait(0.5)
        RunMain(CONFIG.MainURL)
    else
        Status.Text = "Rejected: " .. tostring(data)
        Status.TextColor3 = COLORS.BrightRed
        LogToDiscord(string.format("**Failed Attempt**\nKey: `%s`\nRoblox: `%s`\nReason: `%s`",
            key, LP.Name, tostring(data)))
        local base = Main.Position
        for i = 1, 6 do
            Main.Position = base + UDim2.new(0, (i % 2 == 0 and 8 or -8), 0, 0)
            task.wait(0.04)
        end
        Main.Position = base
    end
end)

OldBtn.MouseButton1Click:Connect(function()
    Status.Text = "Loading BCL 1.1 (OLD)..."
    Status.TextColor3 = COLORS.Yellow
    task.wait(0.3)
    RunMain(CONFIG.OldURL)
end)

print("[Baza.Key] Loader v" .. CONFIG.Version .. " ready. HWID: " .. GetHWID())
