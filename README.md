# clippy-gpt 📎📎📎
Technically, his name is **Clippit**.

`clippy-gpt` is a ChatGPT powered recreation of everyone's favorite paperclip assistant that came bundled in older versions of the Microsoft Office suite. Clippy hangs out on your desktop, patiently waiting to answer any questions you might encounter. You can read more about the original Clippy [here](https://en.wikipedia.org/wiki/Office_Assistant).

## Installation / Configuration
In order to take full advantage of Clippy's AI functionality, you need an OpenAI API Key. Save this key in the enviromental variable `OPENAI_API_KEY`.

In Linux, you can do this by adding something like `export OPENAI_API_KEY='<Your API Key goes here>'` to your `.bashrc` file.

In Windows, you can launch `sysdm.cpl` from the `mod + R` menu. On the `Advanced` tab, press the `Environmental Variables` button. From that screen, you can create a new system variable called `OPENAI_API_KEY` and asign it the value of your API key.

In some setups on both Windows and Linux, a reboot may be needed for these changes to take effect.

You'll need to install the dependencies listed in `requirements.txt`. The process may vary depending on how your system is configured, but generally you can do this by downloading `requirements.txt` and then running

```
pip install -r requirements.txt
```

Once the dependencies are installed, you can download the latest binary from the [releases page](https://github.com/joshuaDeal/clippy-gpt/releases). Make this binary executable, and you should be good to go!

## Building
`clippy-gpt` can be built with PyInstaller.

Again, you must first install all of the dependencies from `requirements.txt` (See above).

Then, run

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
- [clippyjs](https://github.com/pi0/clippyjs) -- The sprite sheet, animation definitions, and sound effects were all source from this project.
- [ClippyVS](https://github.com/tanathos/ClippyVS) -- Clippy in Visual Studio.
- [Clippy](https://github.com/felixrieseberg/clippy) -- Another Clippy as an AI front-end. This one is set up to work with local LLMs. I might go that same direction with this project someday, but I haven't really gotten that deep into toying around with local LLMs yet.

And then of course, there is the original Clippy from Microsoft Office.
