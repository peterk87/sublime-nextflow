# sublime-nextflow: [Nextflow] workflow completions, commands, syntax highlighting and snippets for [Sublime Text 4]

- **WARNING:** Sublime Text 3 is no longer supported by this package. Only Sublime Text 4 is supported (requires Python 3.8 and new features in ST4).
- **NOTE:** Only [DSL-2] Nextflow workflows are supported by this package.

This package provides [Nextflow]

- completions (`params.`, `conda`, `<PROCESS>.out.<emit name>`)
- commands (insert Biocontainer container directive, insert module import statement)
- syntax highlighting
- snippets

Basically a collection of things to make [Nextflow] workflow development a bit easier especially when trying to develop [nf-core] quality workflows.

## Nextflow completions and commands


### Workflow `params`

**NOTE:** Completions and info popups for `params` depend on a valid `nextflow_schema.json` in your workflow root directory. Example [`nextflow_schema.json` for nf-core/viralrecon workflow](https://github.com/nf-core/viralrecon/blob/master/nextflow_schema.json).

Navigate cursor to a `params.<variable>` to show a popup with info pulled from the `nextflow_schema.json` for that workflow parameter.


### [Conda] completion

**NOTE:** [Conda] must be installed along with any channels (e.g. [bioconda], [conda-forge]) to get packages information

- Open the command palette (`ctrl+shift+p`) and run the `Nextflow: Fetch Conda packages information` command to fetch the latest Conda package info (runs `conda search`; may take a while).
- In your process definition, inside the `conda` directive string press `ctrl+space` to bring up the completion list. *This may have a little delay since the package list may be very large.*

```nextflow
process PANGOLIN {
  conda '<press ctrl+space to bring up completion list>'
}
```

## [Biocontainer] insert command

This command inserts similar code to what you'd find in an [nf-core modules](https://github.com/nf-core/modules) process definition with respect to process `container` directives. The container information is pulled from the [Singularity][] images [https://depot.galaxyproject.org/singularity/](https://depot.galaxyproject.org/singularity/) and cached. [Docker] container image tags point to the [Biocontainers][] [Quay.io page](https://quay.io/organization/biocontainers).

- Open the command palette (`ctrl+shift+p`) and run the `Nextflow: Fetch Biocontainers information` command to fetch the latest [Biocontainers] list fetched from 
- In your process definition, press `ctrl+l,c`, search for the container you're interested in

```nextflow
  if (workflow.containerEngine == 'singularity' && !params.singularity_pull_docker_container) {
    container 'https://depot.galaxyproject.org/singularity/pangolin:3.1.5--pyhdfd78af_0'
  } else {
    container 'quay.io/biocontainers/pangolin:3.1.5--pyhdfd78af_0'
  }
```

## Nextflow Syntax Highlighting

Nextflow syntax highlighting extends Sublime Text 4's Groovy syntax with highlighting of: 

- imports (DSL-2 modules)
- workflow definitions
- process definitions
- channel highlighting based on matching `ch_*`
- some invalid syntax checks (into channel in input tag and from channel in output tag)
- highlighting special Nextflow functions and variables (`workflow`, `params`, `task`, etc)

## Nextflow Snippets

- `!env`: `#!/usr/bin/env nextflow`
- `proc`: [process](https://www.nextflow.io/docs/latest/process.html) snippet
- `tag`: [tag](https://www.nextflow.io/docs/latest/process.html#tag) directive snippet
- `pub`: [publishDir](https://www.nextflow.io/docs/latest/process.html#publishdir) directive snippet
- `illumina`: Illumina paired-end reads file pairs channel
- `cpus`: insert "${task.cpus}" into a script
- `script_path`: specify user script (e.g. Python script) to use from `scripts/` directory in workflow base directory
- `info`: `log.info` snippet 
- `done`: on workflow complete or error message

[DSL-2]: https://www.nextflow.io/docs/latest/dsl2.html
[Nextflow]: https://www.nextflow.io/
[nf-core]: https://nf-co.re/
[Conda]: https://docs.conda.io/en/latest/
[bioconda]: https://bioconda.github.io/
[conda-forge]: https://conda-forge.org/
[Singularity]: https://sylabs.io/guides/3.7/user-guide/quick_start.html
[Docker]: https://www.docker.com/
[Sublime Text 4]: http://www.sublimetext.com/
