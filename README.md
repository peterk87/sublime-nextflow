# sublime-nextflow: Nextflow workflow syntax highlighting and snippets for Sublime Text 3

![Insert pretty screenshot here]()

## Nextflow Syntax Highlighting

Nextflow syntax highlighting extends Sublime Text 3's Groovy syntax with highlighting of: 

- processes
  - input/output/script tags
- channel highlighting based on matching `ch_*`
- some invalid syntax checks (into channel in input tag and from channel in output tag)
- highlighting special Nextflow functions and variables (workflow, params, task, etc)

## Nextflow Snippets

- `proc`: [process](https://www.nextflow.io/docs/latest/process.html) snippet
- `tag`: [tag](https://www.nextflow.io/docs/latest/process.html#tag) directive snippet
- `pub`: [publishDir](https://www.nextflow.io/docs/latest/process.html#publishdir) directive snippet
- `init`: initialize a Nextflow workflow (shebang, some initial params and a help message)
- `illumina`: Illumina paired-end reads file pairs channel
- `par`: Create a new params parameter (`params.<param_name> = <default>`)
- `cpus`: insert "${task.cpus}" into a script
- `script_path`: specify user script (e.g. Python script) to use from `scripts/` directory in workflow base directory
- `info`: `log.info` snippet 
