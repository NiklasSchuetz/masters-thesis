Get-ChildItem "." -Filter *.ini | 
Foreach-Object {
    kubectl cp $_.Name controller:$_
}