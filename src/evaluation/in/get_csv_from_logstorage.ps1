$kubectlls = kubectl exec -it logstorage -- ls

foreach ($f in $kubectlls.split("")) {
    if($f -like "*.csv"){
        kubectl cp logstorage:$f $f
        kubectl exec -it logstorage -- rm $f
    }
}
