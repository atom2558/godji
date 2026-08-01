Set WshShell = CreateObject("WScript.Shell")
strUserProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")

Set fso = CreateObject("Scripting.FileSystemObject")

' Path 1: Standard Desktop
strPath1 = strUserProfile & "\Desktop\AI Godji.lnk"
Set oLink1 = WshShell.CreateShortcut(strPath1)
oLink1.TargetPath = "D:\godji\Launch_AI_Godji.bat"
oLink1.WorkingDirectory = "D:\godji"
oLink1.Description = "AI Godji One-Click Master Launcher"
oLink1.Save

' Path 2: OneDrive Desktop
strOneDrive = strUserProfile & "\OneDrive\Desktop"
If fso.FolderExists(strOneDrive) Then
    strPath2 = strOneDrive & "\AI Godji.lnk"
    Set oLink2 = WshShell.CreateShortcut(strPath2)
    oLink2.TargetPath = "D:\godji\Launch_AI_Godji.bat"
    oLink2.WorkingDirectory = "D:\godji"
    oLink2.Description = "AI Godji One-Click Master Launcher"
    oLink2.Save
End If
