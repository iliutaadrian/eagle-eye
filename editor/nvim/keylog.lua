-- Eagle Eye — Neovim mode-aware keystroke logger.
--
-- Logs every keystroke with the current mode (n/i/v/c/...) so Eagle Eye can see
-- editing context the OS-level keylogger cannot. The app's nvim-ingest tails this
-- file into the SQLite DB.
--
-- Install (see editor/nvim/README.md):
--   cp editor/nvim/keylog.lua ~/.config/nvim/lua/eagleeye.lua
--   add to init.lua:  require("eagleeye")
--
-- Writes to: ~/Documents/EagleEye/nvim-YYYY-MM-DD.log

local M = {}

local dir = vim.fn.expand("~/Documents/EagleEye")
vim.fn.mkdir(dir, "p")

local function path()
  return dir .. "/nvim-" .. os.date("%Y-%m-%d") .. ".log"
end

local fh = io.open(path(), "a")
local cur_day = os.date("%Y-%m-%d")
local last_mode = ""
local last_ts = 0

local function reopen_if_new_day()
  local day = os.date("%Y-%m-%d")
  if day ~= cur_day then
    if fh then fh:close() end
    fh = io.open(path(), "a")
    cur_day = day
  end
end

vim.on_key(function(key)
  if not fh then return end
  reopen_if_new_day()

  local mode = vim.api.nvim_get_mode().mode
  local readable = vim.fn.keytrans(key)
  local now = os.time()

  if mode ~= last_mode or (now - last_ts) > 1 then
    fh:write(string.format("\n[%s] %-3s ", os.date("%H:%M:%S"), mode))
    last_mode = mode
  end
  fh:write(readable)
  last_ts = now
end)

local timer = vim.loop.new_timer()
timer:start(3000, 3000, vim.schedule_wrap(function()
  if fh then fh:flush() end
end))

vim.api.nvim_create_autocmd({ "VimLeavePre" }, {
  callback = function()
    if fh then fh:flush(); fh:close(); fh = nil end
  end,
})

vim.api.nvim_create_autocmd({ "BufEnter" }, {
  callback = function(a)
    if fh and a.file and a.file ~= "" then
      reopen_if_new_day()
      fh:write(string.format("\n[%s] --- file: %s\n", os.date("%H:%M:%S"), a.file))
      last_mode = ""
    end
  end,
})

return M
