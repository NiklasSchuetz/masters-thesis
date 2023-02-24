$kubectls = kubectl exec -it controller -- ls

foreach ($f in $kubectls.split("")) {

    if($f -like "*.ini"){
        echo $f
        kubectl exec -it controller -- rm $f
    }
}