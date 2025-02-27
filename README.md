## Project: LLM-Powered Turn-Based Game Player

**Description:**  
This project allows a **Python-based AI agent** to play classic turn-based video games on an emulator. It leverages the **Qwen2.5-VL-3B-Instruct** vision-language model (running via vLLM) to interpret game screens (as images) and decide which controller button to press next. The system integrates directly with game emulators through their APIs to capture screenshots and send inputs, avoiding flaky screen scraping or keyboard emulation. While primarily tested on macOS, the setup is cross-platform (macOS/Linux/Windows) given the chosen tools.

**Key Features:**

- **Multi-Platform Emulation:** Supports multiple consoles (e.g., Game Boy, Game Boy Advance) using emulators with Python or API control. Emphasis on macOS compatibility.
- **Direct Frame Access:** Captures game frames directly from the emulator’s frame buffer for efficiency (using emulator’s API or Python interface) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.button%28%27down%27%29%20pyboy.button%28%27a%27%29%20pyboy.tick%28%29%20,0xC345)) ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=5)).
- **Automated Control:** Programmatically presses game controls via emulator APIs (no manual input needed). The control scheme is modular per game – you can easily adjust which actions are available for different games.
- **LLM Decision-Making:** Uses the Qwen2.5-VL-3B-Instruct model to analyze screenshots and output the next move. The model “sees” the game screen and suggests an action (e.g., _“Press A”_ or _“Move cursor down”_).
- **Stability & Timing:** Ensures inputs are applied at the right time with configurable delays for each game. This prevents the AI from acting too fast or out-of-sync with game state.
- **Optional Memory (Beta):** A toggle-able feature to maintain a summary of game progress using the LLM ([GitHub - jmurth1234/ClaudePlayer: An AI-powered game playing agent using Claude and PyBoy](https://github.com/jmurth1234/ClaudePlayer#:~:text=,frames%20for%20analysis%20and%20debugging)). When enabled, the AI will remember past events (via generated summaries) to inform future decisions – useful for long RPGs where context matters. By default, this is off for simplicity and speed.

## Supported Games/Systems

Currently, the project supports turn-based games on:

- **Nintendo Game Boy / Color:** (Example: Pokémon Red/Blue/Yellow, Gold/Silver) via _PyBoy_ emulator.
- **Nintendo Game Boy Advance:** (Example: Pokémon Emerald, Fire Emblem, Advance Wars) via _mGBA_ emulator (with HTTP control).
- _(Experimental)_ Other systems can be added with additional emulator integrations. The design is modular, so adding SNES or others is possible if a suitable API can be found.

_Note:_ You must have the ROM files for the games (not included for copyright reasons). Place the ROMs in a folder and update the config or command-line arguments to point to them.

## Installation

1. **Python Setup:** Install Python 3.10+ (recommended for compatibility). Ensure you have pip available.
2. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/llm-game-player.git
   cd llm-game-player
   ```
3. **Python Dependencies:** Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

   The requirements include:

   - `pyboy` – Game Boy emulator with Python API ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=The%20instructions%20are%20simple%3A))
   - `requests` – for HTTP calls to mGBA
   - `pillow` – for image processing (screenshots)
   - `transformers` and `qwen-vl-utils` (if interacting with Qwen model directly)
   - any additional libraries for vLLM or the model API.  
     _(If using a specific vLLM HTTP server client, include that or use Python’s `requests` to call it.)_

4. **Install Emulators:**

   - **PyBoy:** This is installed via pip already. No separate emulator executable is needed, as PyBoy runs the Game Boy emulation in Python.
   - **mGBA:** Download the latest mGBA emulator for your OS from the [official site](https://mgba.io) and install it (for macOS, you can use Homebrew: `brew install mgba`).
   - **mGBA-HTTP interface:** Download `mGBA-http` from its [GitHub Releases] ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=However%2C%20HTTP%20requests%20are%20pretty,to%20the%20raw%20underlying%20socket)). Choose the release matching your OS (for example, a `.tar.gz` or `.zip` for macOS/Linux, or `.exe` for Windows). Extract it. You should have an `mGBA-http` executable and a `mGBASocketServer.lua` script. Place them in a convenient location.
   - _(Optional)_ If adding other emulators, install those as needed.

5. **Model Setup (Qwen2.5-VL):**

   - **Option A: vLLM Server:** Launch the vLLM server hosting Qwen2.5-VL-3B-Instruct. Follow vLLM’s documentation to start it with the Qwen model. Confirm it’s reachable (e.g., via `http://localhost:8000` or similar).
   - **Option B: Local Transformers:** If not using vLLM’s server API, you can run the model in the Python script. Install `transformers` and the Qwen model weights. For example:
     ```bash
     pip install "git+https://github.com/huggingface/transformers" accelerate
     pip install qwen-vl-utils[decord]==0.0.8
     ```
     This ensures the Qwen model and its image-handling utils are available ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=and%20Transformers)) ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=We%20offer%20a%20toolkit%20to,it%20using%20the%20following%20command)). The script can then load the model with `QwenForConditionalGeneration.from_pretrained("Qwen/Qwen2.5-VL-3B-Instruct")`. Note this requires a GPU for feasible speed.
   - Ensure that you have access to a GPU if possible, as Qwen2.5-VL is large (3B params with vision) – running on CPU will be extremely slow.

6. **System Configuration:**  
   Edit the configuration file (e.g., `config.yaml` or Python constants) to specify:
   - Path to your game ROM(s) and which emulator to use for each. For example:
     ```yaml
     games:
       pokemon_red:
         rom: "/path/to/PokemonRed.gb"
         emulator: "pyboy"
         actions: ["Up", "Down", "Left", "Right", "A", "B", "Start", "Select"]
         action_delay: 0.5 # seconds to wait after an action
       pokemon_emerald:
         rom: "/path/to/PokemonEmerald.gba"
         emulator: "mgba"
         actions:
           [
             "Up",
             "Down",
             "Left",
             "Right",
             "A",
             "B",
             "L",
             "R",
             "Start",
             "Select",
           ]
         action_delay: 1.0 # maybe longer for GBA animations
     ```
   - vLLM or model API details (e.g., URL and port of the model server, or a flag to use local inference).
   - Toggle for the summary feature if you want it on.
   - Any other parameter (like max turns, logging verbosity, etc.).

## Usage

### Running the AI Player

Once setup is done, you can run the AI agent on a game:

```bash
python play_game.py --game pokemon_red --summary off
```

Replace `pokemon_red` with the key of the game you configured (or provide a path/identifier for the ROM directly). The script will:

- Launch or connect to the appropriate emulator for the game. For PyBoy, it will create an emulator instance in the script. For mGBA, make sure **before running the script** that you have mGBA open with the ROM loaded and the mGBA-http server running. _(Tip:_ open a terminal and run `./mGBA-http` from the directory you extracted it, then in the mGBA emulator, load the Lua script via Tools > Scripting.) ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=In%20short%3A)). Once you see mGBA-http’s Swagger UI available at `http://localhost:5000`, you know it's ready.)
- Enter the decision loop: capturing frames and querying the LLM for actions. You’ll see log output each turn, e.g. “Model suggests: Press A”, then “Executing: A”.
- The game will proceed turn by turn under AI control. For instance, in Pokémon, the AI will navigate the menus and choose moves in battle. In strategy games, it will select units or menu options based on the screen.

You can stop the script with `Ctrl+C` if needed. If the game reaches a natural end (not always detectable), you may have to stop manually. Logged actions and occasional screenshots might be saved to the `logs/` directory for review (depending on config).

**Note:** The first turn may be slower due to model loading. Subsequent turns should be a bit faster. Qwen2.5-VL might take a couple of seconds to respond each time.

### Using the Optional Summary Feature

By default, the agent makes decisions only based on the current screen. If you want the agent to have memory of what happened earlier, enable summaries:

```bash
python play_game.py --game pokemon_red --summary on
```

With this, the agent will periodically summarize past events. For example, it might remember previous battles or objectives. This can improve decision-making in games where the context carries over (e.g., remembering that the player’s health is low or a certain item was picked up). The summary will be printed in logs so you can see what the AI “thinks” has happened so far. Keep in mind this feature is experimental – sometimes the summaries might be imperfect. If you notice the model getting confused, you can turn this feature off.

### Configuring Timing and Controls

Each game’s entry in the config can have an `action_delay` (in seconds) or similar parameter. If the AI is inputting too quickly or too slowly, tweak this value. For instance, if playing a fast menu-based game, you might reduce the delay so it navigates menus quicker. For games with lengthy animations, increase the delay so the AI waits for them to finish. The goal is to ensure the screen shown to the AI for the next decision is the correct one (after all effects of the last action have occurred).

The `actions` list in the config defines what buttons the AI is allowed to press. By limiting this, you can prevent unnecessary inputs. For example, if a game never uses the "Select" button, you can omit it. This also helps the LLM by restricting the vocabulary of actions (we instruct it only to use these).

### Extending to New Games or Emulators

To add a new game, you’ll need a compatible emulator. If it’s a GB/GBA game, just adding a new config entry is sufficient (as those consoles are already handled by PyBoy or mGBA). For a new console, you may have to implement a new emulator interface in the code. For example, to support SNES, you could integrate an emulator like Snes9x or a RetroArch core. The code is organized so that adding a new class for an emulator and hooking it into the main loop is straightforward. Avoid using any emulator that cannot be automated; but if you must, implement a minimal OS-level control as a last resort.

Be sure to update the config with appropriate keys (e.g., SNES might have "X", "Y" buttons, etc.) and any special timing considerations.

## Examples

- **Pokémon Red (GB)**: The AI will start a new game or continue from a save. It will navigate the menus, walk around, and engage in turn-based battles. For instance, in battle it will choose fight/run/etc based on the screen. Since Pokémon is heavily text-based, Qwen’s strong vision+OCR capability is helpful in reading the health bars and move names ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=capable%20of%20analyzing%20texts%2C%20charts%2C,graphics%2C%20and%20layouts%20within%20images)).
- **Pokémon Emerald (GBA)**: The AI will control the character similar to above. Ensure mGBA and mGBA-http are running. You might see the AI wandering or exploring. Turn-based battles will be handled, but outside of battle, the AI has free movement (it might not always make sensible exploration decisions since this is a simple prompt-based AI, not a trained policy).
- **Tetris (as a test, though not turn-based)**: If you try on Tetris via PyBoy (just as a fun test), the model might not perform well because it’s not a turn-based game and requires real-time planning – this system is not designed for that, so results will vary. It’s just to illustrate you could plug in other games.

## Troubleshooting

- **Emulator connection issues:** If the script cannot connect to mGBA-http (errors on HTTP requests), ensure that you started `mGBA-http` _and_ loaded the Lua script into mGBA. Also check that the port matches (default is 5000). You can test via a browser: go to `http://localhost:5000/index.html` to see the Swagger UI ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=Once%20running%20you%20quickly%20begin,http%3A%2F%2Flocalhost%3A5000%2Findex.html)). If that doesn’t load, the server isn’t running.
- **PyBoy errors on Mac:** PyBoy may require SDL2. If you get an error about SDL or no display, try installing SDL2 (`brew install sdl2`) and ensure you’re not running headless if you want a window. For headless mode on Mac, you might need to allow the application to use offscreen rendering (usually not an issue). If performance is low, remember PyBoy can disable rendering entirely for speed ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=Performance%20is%20a%20priority%20for,scripts%20as%20fast%20as%20possible)), but then you won’t see a window (the AI still works).
- **Model not responding or slow:** Confirm that the Qwen model is properly loaded. If using local inference, check that your machine has enough VRAM. If using vLLM server, ensure the server log shows requests coming in. If the model outputs gibberish or unrelated text, the prompt may need refining – make sure you followed the prompt format suggestions in the config (the AI’s system prompt should instruct it to focus on the game and output an action).
- **LLM output is inconsistent:** Sometimes the LLM might say something like "I will press the A button now." If our parser expects just "A", it might fail. In such cases, we can either improve the parsing or adjust the prompt to say "Respond with the name of the button only." This might require iterating on the prompt design.
- **Game state not updating:** If the AI seems to do an action but then reads the same screen again (stuck in a loop), it likely means our delay was too short (the AI took a screenshot before the game registered the input). Increase the delay a bit for that game and try again. Also check if the input was actually sent – for PyBoy, did we call `tick()` after pressing? For mGBA, did the HTTP endpoint return success?

## Project Structure

- `play_game.py` – Main entry script that parses arguments and runs the loop.
- `emulators/` – Package containing emulator interface classes (PyBoyEmulator, MGBAEmulator, etc.).
- `model/` – Code for interacting with the Qwen model (prompt construction, API calls, response parsing).
- `config.yaml` – Configuration for games and system settings.
- `PLAN.md` – In-depth implementation planning document (for developers).
- `README.md` – (this file) Usage and overview documentation.

## Acknowledgments and References

- **PyBoy Emulator:** Thanks to the open-source PyBoy project for providing a Python Game Boy emulator with a controllable API ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.set_emulation_speed%280%29%20,0xC345)) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.button%28%27down%27%29%20pyboy.button%28%27a%27%29%20pyboy.tick%28%29%20,0xC345)). This made integration with GB/GBC games seamless.
- **mGBA and mGBA-http:** The mGBA emulator (enduring thanks to its developers) and Niko Uusitalo’s mGBA-http project for enabling cross-platform control of mGBA via HTTP ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=However%2C%20HTTP%20requests%20are%20pretty,to%20the%20raw%20underlying%20socket)) ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=5)), which we utilize for GBA games.
- **Qwen2.5-VL Model:** Developed by Alibaba Cloud (Qwen team). This powerful vision-language model ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=capable%20of%20analyzing%20texts%2C%20charts%2C,graphics%2C%20and%20layouts%20within%20images)) provides the “brains” for our agent to interpret game visuals and was integrated using Hugging Face Transformers and vLLM for serving.
- **Claude Player Project:** Inspiration was drawn from the ClaudePlayer project by jmurth1234 ([GitHub - jmurth1234/ClaudePlayer: An AI-powered game playing agent using Claude and PyBoy](https://github.com/jmurth1234/ClaudePlayer#:~:text=%2A%20AI,game%20and%20manage%20its%20state)), which demonstrated an AI (Claude) playing Pokémon via PyBoy, including techniques like summarization. Our implementation adapts similar ideas using Qwen and extends support to GBA.
- **OpenAI Gym Retro:** OpenAI’s Gym Retro was an initial inspiration for thinking about generalizable game interfaces ([What has replaced OpenAI Retro Gym? : r/reinforcementlearning](https://www.reddit.com/r/reinforcementlearning/comments/11whc6d/what_has_replaced_openai_retro_gym/#:~:text=OpenAI%20Retro%20Gym%20hasn%27t%20been,and%20gym%20to%20get%20installed)). We opted for direct emulator APIs due to Retro’s maintenance issues ([What has replaced OpenAI Retro Gym? : r/reinforcementlearning](https://www.reddit.com/r/reinforcementlearning/comments/11whc6d/what_has_replaced_openai_retro_gym/#:~:text=OpenAI%20Retro%20Gym%20hasn%27t%20been,and%20gym%20to%20get%20installed)), but the concept of treating game emulation as a reinforcement learning environment influenced our design.

With this setup, you can watch an AI agent make decisions in classic games. Keep in mind that the AI's intelligence is limited by the prompt and model – it doesn't learn from reward signals as in reinforcement learning, but rather tries to _interpret_ and _do the right thing_ based on its training. This can lead to surprising successes or hilarious missteps. Feel free to experiment with different prompts or even fine-tune the model on game transcripts for better results.

Enjoy watching Qwen play your favorite turn-based games, and happy hacking!
