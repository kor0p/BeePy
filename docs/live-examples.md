# Welcome to BeePy

<script src='https://unpkg.com/@kor0p/beepy@0.10.0/dist/beepy.js'></script>
<script>
beepy.__main__ = async () => {
    for (const demo_file of ['counter', 'synced_counters']) {
        await beepy.enterModule(`../demo/${demo_file}`)
    }
}
</script>

## Try it yourself at [sandbox](https://kor0p.github.io/BeePy-examples/sandbox){target=_blank}

<div id="beepy-examples" class="grid cards" markdown>

- :material-file-code: Code

    === "1️⃣"

        ``` python title="Counter"
        --8<-- "docs/demo/counter.py"
        ```

    === "2️⃣"

        ``` python title="Synced Counters"
        --8<-- "docs/demo/synced_counters.py"
        ```

- 🎉 Result

    === "1️⃣"
        <pre><div id="ex-counter"></pre>

    === "2️⃣"
        <pre><div id="ex-synced-counters"></pre>

</div>
