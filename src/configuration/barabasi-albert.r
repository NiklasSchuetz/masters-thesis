library(igraph)


args <- commandArgs()

# print(args) # uncomment to see why 6,7,8,9 of args list is used


if (length(args) != 0) {
    filename <- args[9]

    my_graph <- sample_pa(
        n = args[6],
        m = args[7],
        power = args[8],
        directed = FALSE,
        algorithm = "psumtree"
    )


    write_graph(
        graph = my_graph,
        file = filename,
        format = "graphml"
    )
} else {
    powersteps <- c(2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3)

    r <- 1:10

    for (p in powersteps) {
        for (i in r) {
            my_graph <- sample_pa(
                n = 200,
                m = 6,
                power = p,
                directed = FALSE,
                algorithm = "psumtree"
            )


            name_vector <- c(
                "configuration/networks/generatedNetworks/ba/",
                "ba_", toString(p),
                "_", toString(i), ".graphml"
            )

            write_graph(
                graph = my_graph,
                file = paste(name_vector, collapse = ""),
                format = "graphml"
            )
        }
    }
}
