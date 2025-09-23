# clippy-gpt 📎📎📎
Technically, his name is **Clippit**.

`clippy-gpt` is an AI powered recreation of everyone's favorite paperclip assistant that came bundled in older versions of the Microsoft Office suite. Clippy hangs out on your desktop, patiently waiting to answer any questions you might encounter. You can read more about the original Clippy [here](https://en.wikipedia.org/wiki/Office_Assistant).

https://github.com/user-attachments/assets/078a9933-bde8-41b9-ba49-c847dc447816

## Installation / Configuration
There are three ways to take advantage of Clippy's AI functionality.

### Running LLMs Locally
Your first option would be to download a large language model to run locally, however, it should be noted that in order to do this effectively, you need to have higher-end computer hardware. You can download models in `.gguf` format from websites like [Hugging Face](https://huggingface.co/). You might consider downloading a model like [TinyLlama-1.1B-Chat-v1.0-GGUF](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf) to start out with.

### Using A Service
Alternatively, you can use either the OpenAI or OpenRouter API to power clippy via an online AI service. You'll need to save an api key in an environmental variable like `OPENAI_API_KEY` or `OPENROUTER_API_KEY`. I have included OpenRouter as an option because it provides some degree of free access to online AI models, unlike OpenAI, which, as of this writing, does not offer any free AI solutions via their API.

In Linux, you can create a new environmental variable by adding something like `export OPENAI_API_KEY='<Your API Key goes here>'` to your `.bashrc` file. Then, run something like `source ~/.bashrc`.

In Windows, you can launch `sysdm.cpl` from the `mod + R` menu. On the `Advanced` tab, press the `Environmental Variables` button. From that screen, you can create a new system variable called `OPENAI_API_KEY` and assign it the value of your API key.

In some setups on both Windows and Linux, a reboot may be needed for these changes to take effect.

You can download the latest binary from the [releases page](https://github.com/joshuaDeal/clippy-gpt/releases). Make this binary executable, and you should be good to go!

## Usage
`clippy-gpt`'s behavior can be tweaked via command line arguments.

```
usage: clippy-gpt [-h] [-l PATH | -a MODEL | -r MODEL]

Friendly paperclip AI assistant.

options:
  -h, --help            show this help message and exit
  -l, --local PATH      Specify file path to local model.
  -a, --openai MODEL    Specify OpenAI model to use.
  -r, --openrouter MODEL
                        Specify OpenRouter model to use.
```

- `--local PATH` runs using local models. The `PATH` should point to the `.gguf` model you'd like to use.
- `--openai MODEL`/`--openrouter MODEL` can be used to override the default models used when using these services.

For example,
```
clippy-gpt -r x-ai/grok-4-fast:free
``` 
will run using the free version of 'Grok 4 Fast' from OpenRouter.

## Building
`clippy-gpt` can be built with PyInstaller.

You'll need to install the dependencies listed in `requirements.txt`. The process may vary depending on how your system is configured, but generally you can do this by running

```
pip install -r requirements.txt
```

Then, to build, run

```
pyinstaller main.spec
```

from inside of the git repository's root directory.

This should create a directory called `dist/` inside of which you should see a new binary file.

## Why?
Clippy got a lot of hate in his day, but I always liked the little guy! I have fond memories from the elementary school computer lab, where instead of writing my essays like I should have been, I'd spend entire class periods cycling though all of Clippy's animations and dragging him around the screen to funny positions. Now, I can do that all over again. I suppose I never really grew up much. ¯\\\_(ツ)\_/¯

## Contributing
Contributions are always welcome! Just open an issue about any bugs/feature requests/etc. If you want to address what you found yourself, fork it to pull request pipeline. I'll merge anything that looks cool. (I'm a bit of a novice when it comes to collaborating on GitHub but I think this is generally what the process looks like.) For anything more nuanced, you can always reach out to me.

## Also See
This is a list of projects that proved to be extremely valuable resources when trying to create `clippy-gpt`. I highly recommend you check them out and consider giving them a star or whatever it is people do to show appreciation to a project on GitHub.
- [clippyjs](https://github.com/pi0/clippyjs) -- The sprite sheet, animation definitions, and sound effects were all sourced from this project.
- [ClippyVS](https://github.com/tanathos/ClippyVS) -- Clippy in Visual Studio.
- [Clippy](https://github.com/felixrieseberg/clippy) -- Another Clippy as an AI front-end. This one is set up to work with local LLMs.

And then of course, there is the original Clippy from Microsoft Office.
