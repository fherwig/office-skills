-- Run JavaScript in the first Chrome tab whose URL contains argv[1].
-- usage: osascript chrome_js.applescript <url-fragment> <javascript>
-- Needs Chrome: View > Developer > Allow JavaScript from Apple Events (the person switches it on).
-- NOTE: this runs in an ISOLATED world: page globals (UserID, TimeOfSlot...) are invisible.
-- To touch page state, inject a <script> element (see when2meet.py, main_world).
on run argv
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains (item 1 of argv) then
                    return execute t javascript (item 2 of argv)
                end if
            end repeat
        end repeat
    end tell
    return "NO TAB"
end run
