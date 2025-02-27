## 1. Overview and Goals

This plan outlines a system for a Python-based AI agent to play turn-based video games via emulators. We will use the **Qwen2.5-VL-3B-Instruct** model (a multimodal vision-language LLM) hosted on a vLLM server as the decision-making engine. The AI agent will observe game screens and output actions, which we then execute in the emulator. Key design goals include cross-platform support (with emphasis on macOS), efficient frame capture via emulator APIs, modular per-game control schemes, minimal external automation, optional game state summarization by the LLM, and stable/timed execution of inputs.

**Status: Initial Implementation Complete**
- Core emulator interfaces built for PyBoy (GB/GBC) and mGBA (GBA)
- Basic LLM agent implemented with Qwen2.5-VL model integration
- Main game loop connecting emulators and model
- Configuration system for games and model settings
- Testing utilities for emulator connections

## 2. Emulator Selection (Cross-Platform)

**Identify the best emulator for each target game**, prioritizing those with direct Python control and screenshot capabilities:

- **Game Boy / Game Boy Color (e.g., Pokémon Red/Blue/Gold):** Use **PyBoy**, a Game Boy emulator written in Python ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=Getting%20Started)) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.button%28%27down%27%29%20pyboy.button%28%27a%27%29%20pyboy.tick%28%29%20,0xC345)). PyBoy runs on multiple platforms and exposes a Python API to load ROMs, step frames, read memory, simulate button presses, and capture the screen. This provides a pure-Python, cross-platform solution for GB/GBC games, which is ideal for macOS as well.

- **Game Boy Advance (e.g., Pokémon Emerald, Advance Wars):** Use **mGBA** (a cross-platform GBA emulator) with the **mGBA-HTTP** interface ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=However%2C%20HTTP%20requests%20are%20pretty,to%20the%20raw%20underlying%20socket)). The mGBA emulator itself runs on Windows, Linux, and macOS, and the `mGBA-http` tool wraps mGBA's scripting API in a local HTTP server, allowing any language (including Python via HTTP requests) to control the emulator ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=After%20having%20done%20some%20investigation%2C,controlling%20commands%20to%20an%20emulator)). This avoids OS-specific key injection by leveraging a built-in socket API. mGBA-HTTP supports sending gamepad inputs and capturing screenshots through simple HTTP calls ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=5)). (Ensure to download the appropriate mGBA-http binary for your OS from its releases, and the accompanying Lua script for mGBA's scripting interface.)

- **Other Consoles (if needed):** If the previously listed games include other turn-based titles (e.g., SNES or NES RPGs), prefer an emulator with a programmatic interface. For example, **Libretro/RetroArch** cores can be controlled via Python through the Gym Retro interface (OpenAI Retro) ([What has replaced OpenAI Retro Gym? : r/reinforcementlearning](https://www.reddit.com/r/reinforcementlearning/comments/11whc6d/what_has_replaced_openai_retro_gym/#:~:text=OpenAI%20Retro%20Gym%20hasn%27t%20been,and%20gym%20to%20get%20installed)), though note Gym Retro is outdated and may require older Python versions ([What has replaced OpenAI Retro Gym? : r/reinforcementlearning](https://www.reddit.com/r/reinforcementlearning/comments/11whc6d/what_has_replaced_openai_retro_gym/#:~:text=OpenAI%20Retro%20Gym%20hasn%27t%20been,and%20gym%20to%20get%20installed)). If a direct API isn't available for a specific game’s emulator, as a **last resort** use OS-level automation (e.g., `pyautogui` for key presses and `mss` or `PIL.ImageGrab` for screenshots) – this ensures coverage of any platform, but we avoid it unless necessary due to stability concerns ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=After%20having%20done%20some%20investigation%2C,controlling%20commands%20to%20an%20emulator)).

**Cross-platform considerations:** Both PyBoy and mGBA (with mGBA-http) are cross-platform, so the core system will work on macOS (priority) and also on Linux/Windows with minimal changes. PyBoy uses SDL2/OpenGL for rendering, which works on macOS, but ensure SDL2 is installed on Mac (e.g., via Homebrew) if needed for the PyBoy window. mGBA-http is built in .NET (C#) but packaged as a self-contained binary per OS ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=mGBA%20is%20cross,platform.%20Perfect)) – you can run the macOS or Linux binary without installing .NET separately. This design avoids platform-specific dependencies: by using HTTP and Python APIs, we ensure the solution remains portable.

## 3. Emulator Integration and Control Interface

To maintain a **modular control scheme**, abstract the emulator interactions behind a common interface so we can tailor controls per game if needed:

- **Define a GameEmulator Interface:** Create a Python class (or set of classes) that defines methods such as `load_game(rom_path)`, `get_frame()` (to retrieve the current framebuffer or screenshot), and `send_input(action)` (to press a game control). We will implement this interface for each emulator type (PyBoy and mGBA). This modular design allows adding new emulators or game-specific control tweaks by extending the interface, rather than altering core logic.

- **PyBoy Implementation:** Use PyBoy’s API to load the ROM and manage the game loop. For example, initialize with `pyboy = PyBoy('path/to/game.gb', window='headless')` (headless or SDL window as needed) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=Or%20use%20it%20in%20your,Python%20scripts)). Use PyBoy’s methods to press buttons and advance frames: e.g., `pyboy.set_emulation_speed(0)` (remove speed limit for faster-than-real-time if desired) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.set_emulation_speed%280%29%20,0xC345)), and `pyboy.press_button('A')` / `pyboy.release_button('A')` or the convenience `pyboy.button('A')` for a quick tap ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.set_emulation_speed%280%29%20,0xC345)). After sending input, call `pyboy.tick()` to advance the emulator by one frame (or a few frames) so the input is processed ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.set_emulation_speed%280%29%20,0xC345)). The interface’s `get_frame()` can fetch the latest frame as an image via `pyboy.screen_image()` or `pyboy.screen.image` (which provides a PIL image of the current screen) ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.button%28%27down%27%29%20pyboy.button%28%27a%27%29%20pyboy.tick%28%29%20,0xC345)). PyBoy also allows reading memory or game state if needed, which could help determine when a turn is over (though our primary method will be via screen content).

- **mGBA-HTTP Implementation:** Launch the mGBA emulator and load the Lua scripting server (`mGBASocketServer.lua`) via _Tools > Scripting_ in the mGBA GUI (this step can be manual or automated if mGBA supports command-line script loading). Then start the `mGBA-http` server (which listens on a port, e.g., 5000). In Python, use the `requests` library to communicate with this server:

  - **Loading the game:** Once mGBA is running, load the ROM file through the mGBA UI or via an HTTP call if available (mGBA-http might have an endpoint `/core/loadrom?path=...`). Alternatively, start mGBA with the ROM pre-loaded via command line.
  - **Sending Input:** Use HTTP POST requests to endpoints like `/gamepad/press` or `/gamepad/release` with query parameters or JSON specifying which button to press. (Refer to mGBA-http documentation for exact endpoints; for example, it likely provides endpoints for each button or a general input endpoint. In absence of exact docs here, plan to map actions "A", "B", "UP", etc., to the corresponding calls.)
  - **Frame Advance:** For turn-based games, we might run mGBA continuously (it will be ticking internally). However, to sync with the AI loop, consider pausing the emulator until an input is given. If needed, mGBA’s `/emulator/pause` and `/emulator/unpause` or stepping frame-by-frame could be used. A simpler approach is to let the emulator run normally, and just request screenshots at appropriate times, since turn-based games generally wait for player input. Ensure that after sending an input, we allow enough time (or frames) for the game to update (we can possibly step a certain number of frames via an endpoint, or simply wait and then grab the next frame).
  - **Capturing Screenshots:** Use the `/core/screenshot` endpoint of mGBA-http ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=5)). This endpoint requires a file path parameter (on the host machine) to save the screenshot. Implement `get_frame()` by calling this endpoint (POST request with a unique file path for each call or a fixed path overwritten each time), then reading the image file into a PIL Image or bytes. The mGBA-http screenshot call is fast and avoids the overhead of full screen capture ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=import%20requests)). (We will need to clean up or reuse the screenshot file to avoid clutter.)

- **Modular Action Mappings:** Define an action set for each game or console. For example, a Pokemon game might have actions like `{"Up", "Down", "Left", "Right", "A", "B", "Start", "Select"}`. Our AI (LLM) will decide on high-level actions (e.g., "move up", "press A"), which we then map to these button presses. We can maintain a mapping dictionary per game if needed (though often the console’s standard buttons suffice). Keeping this mapping configurable per game allows custom control (for instance, disabling unused buttons or adding composite actions if a game requires pressing multiple buttons together). The interface’s `send_input(action)` will translate a logical action into emulator-specific input commands (for PyBoy, call `pyboy.press_button(button)` etc., for mGBA, send the HTTP request). This modular design means adding a new game or changing controls doesn’t require changing the core loop or LLM logic – just update the mapping or emulator adapter for that game.

- **Avoid External Automation Tools:** Because we use PyBoy and mGBA’s APIs, we do not rely on external keyboard/mouse automation (no `pyautogui` or OS-specific GUI scripting) for these games ([Use Any Language to Control mGBA](https://www.nikouusitalo.com/blog/use-any-language-to-control-mgba/#:~:text=After%20having%20done%20some%20investigation%2C,controlling%20commands%20to%20an%20emulator)). This yields more stability and consistency. Only if a specific emulator has no API (not covered by PyBoy or mGBA) would we consider a small module using, say, `pynput` or `pyautogui` to send keystrokes to the emulator window and `mss` or `PIL.ImageGrab` to capture the window image. Such a module can be designed as another implementation of the GameEmulator interface, reserved for games where no direct integration is possible. (This is a **fallback** and would require careful handling of window focus and OS permissions, especially on macOS which requires enabling accessibility permissions for automation.)

## 4. Frame Capture Strategy

Efficient frame capture is crucial for performance and accuracy of the AI’s observations. We will use **emulator-provided frame data** wherever possible, as it's more direct and faster than capturing the OS screen:

- **Using Emulator APIs:** PyBoy’s `screen.image` property gives direct access to the current framebuffer image in memory ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=pyboy.button%28%27down%27%29%20pyboy.button%28%27a%27%29%20pyboy.tick%28%29%20,0xC345)). This avoids any display re-render overhead and provides a Pillow Image we can directly feed into our model. Similarly, mGBA-http’s screenshot function captures the emulator’s frame buffer at the moment of the call ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=5)). These methods are efficient and ensure we get the exact game image (with correct resolution and no scaling issues). We will convert these images to the format needed by Qwen (likely an in-memory image or base64 encoding, depending on how the model expects input).

- **Frame Timing:** In turn-based games, it’s not always necessary to capture 60 FPS. We only need a new frame when the game state changes or when awaiting the next user action. The control loop can be event-driven: after each action, wait until the game is ready for the next decision, then capture a frame. For example, in Pokémon, after each move in battle or each menu navigation, there is usually a moment where the game awaits input (like a menu open or a dialog). We can either periodically check (every few frames or a short delay) or if possible detect a known visual cue (like the end of text box or a blinking prompt). A simpler approach is to insert a short fixed sleep (or a loop of `tick()` calls) after each action and then grab the frame. We'll fine-tune these delays per game if needed (see **Timing** below).

- **Optimizations:** PyBoy allows running without rendering or with frame-skipping ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=Performance%20is%20a%20priority%20for,scripts%20as%20fast%20as%20possible)), which could massively speed up an AI trying to brute-force many steps. However, since we have a vision model in the loop (which is relatively slow and needs each frame to be processed), ultra-fast frame generation is less of a priority than synchronization. We will run the emulator at normal or modestly faster-than-real-time speeds to keep the sequence of frames correct. If needed, we can enable frame-skip (only render every Nth frame) to skip unimportant frames (e.g., idle animation frames). We ensure the agent always sees the latest relevant game state when making decisions, rather than every single frame.

## 5. LLM Integration (Qwen2.5-VL-3B-Instruct via vLLM)

The AI brain of the system is the Qwen2.5-VL-3B-Instruct model, which can take an image and a prompt and output text (e.g., the next action or a description). Our integration approach:

- **Model Serving:** We assume the Qwen model is running on a vLLM server (which provides high-throughput, low-latency inference ([Deploy Qwen 2.5 3B Instruct One-Click App - Koyeb](https://www.koyeb.com/deploy/qwen-2-5-3b-instruct#:~:text=Deploy%20Qwen%202,latency))). The vLLM setup might expose a RESTful API or an OpenAI-compatible API. We will need a way to send the current game frame (image) and a textual prompt to the model and receive the model’s response. If using vLLM’s HTTP interface, format a request with the image included. Qwen’s documentation shows that it accepts image input via a special format: e.g., providing a JSON with `{"type": "image", "image": "file://..."} ` and `{"type": "text", "text": "...prompt..."}` ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=match%20at%20L279%20%7B,the%20similarities%20between%20these%20images)), or using the `process_vision_info` utility to prepare inputs ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=match%20at%20L250%20image_inputs%2C%20video_inputs,text%5D%2C%20images%3Dimage_inputs)). In practice, we can send the image in base64 or as a URL if the model supports it ([Qwen/Qwen2.5-VL-3B-Instruct - Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=We%20offer%20a%20toolkit%20to,base64%2C%20URLs%2C%20and%20interleaved)) ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=%22type%22%3A%20%22image%22%2C%20%22image%22%3A%20%22https%3A%2F%2Fqianwen,)). (One approach is to save the frame image to a temporary file or serve it from a local HTTP server that vLLM can fetch; or since vLLM is local, possibly pass the image array directly if using a Python client library.)

- **Prompt Design:** Construct a prompt that guides the LLM to output a game action. For example, we might prompt the model with a system message like: _"You are playing a game. Analyze the image and decide the best next move. Respond with a single action (e.g., 'Press A', 'Move Up', 'Select Attack', etc.)"_ Then include the image of the current screen as context, and possibly additional info like the last few textual observations (if any text was on screen that the model might not fully read from pixels). Qwen2.5-VL is capable of OCR and understanding screen text ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=capable%20of%20analyzing%20texts%2C%20charts%2C,graphics%2C%20and%20layouts%20within%20images)), but to improve reliability we might also provide any easily accessible state (for example, if emulator memory gives us the exact text strings or menu options, we could append those as text). The model being _Instruct_-tuned means it will follow instructions given in the prompt to output the desired format.

- **LLM Output Parsing:** Since we want a discrete action, we should constrain the LLM’s output format. The prompt can say “respond _only_ with an action command”. For example, if the game is Pokemon, valid outputs might be "Up", "Down", "A", "B", etc., or higher-level like "Open Menu" which we then map to a button sequence. The simplest method is to have it output the name of a button (or a short phrase) which we map in a lookup table. We'll implement a parser that takes the model’s text output and normalizes it to one of the known actions. (For instance, if the model says "press A", we map that to the action `"A"`; if it says "go up", map to `"Up"`.) This parser can be a set of keyword checks for each valid action or a regex. It's important for stability to handle synonyms or unexpected phrasing gracefully – possibly by reprompting or defaulting to a no-op if uncertain. However, by instructing the model to use a consistent format (even JSON or one-word outputs), we reduce parsing complexity.

- **Model Iteration Loop:** The main loop will be:

  1. Capture current frame via emulator API.
  2. Send frame (and context) to Qwen model via vLLM.
  3. Receive the model’s suggested action (text).
  4. Parse it to a concrete emulator input.
  5. Execute the input in the emulator.
  6. Repeat.  
     We will incorporate checks to break the loop if the game ends or on a certain condition (for example, if the model outputs "quit" or if a maximum number of turns is reached).

- **Performance:** Qwen2.5-VL-3B is a 3B-parameter model with vision capabilities, so running it might take on the order of 1-2 seconds per inference on a decent GPU ([Qwen/Qwen2.5-VL-3B/7B/72B-Instruct are out!! : r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1itq30t/qwenqwen25vl3b7b72binstruct_are_out/#:~:text=Qwen%2FQwen2.5,is%20a%20change%20in)). vLLM helps throughput, but the inference time is still a consideration. Since turn-based games don't require real-time reactions (a delay of a second per move is acceptable), this should be fine. If performance is an issue, an alternative is to use a smaller or more specialized model for quick image recognition (like detecting menu options) and reserve the LLM for higher-level decisions, but that adds complexity. For the scope of this project, using Qwen alone is acceptable, acknowledging that the gameplay will proceed at a slower pace than a human but consistently.

## 6. Optional Game State Summarization (Memory System)

To enable the AI to remember past events or long-term context without sending a long history of images to the model every turn, we introduce an **optional "history summarization" feature**. This will be off by default (to keep the system simpler and reduce model calls), but can be toggled on for games where long-term strategy or story context is important.

- **Rationale:** Large language models have context windows, and repeatedly sending every past observation could be inefficient. Instead, we can periodically summarize the game progress into a concise description that the model can refer to. The Claude-based project _Claude Player_ implemented a similar idea, generating periodic summaries of game progress to maintain context ([GitHub - jmurth1234/ClaudePlayer: An AI-powered game playing agent using Claude and PyBoy](https://github.com/jmurth1234/ClaudePlayer#:~:text=,frames%20for%20analysis%20and%20debugging)). We will do the same with Qwen or a text-only model.

- **Implementation:** Maintain a buffer of recent key events or observations after each turn. For instance, if the model just chose an action and the game responded (maybe some text on screen like "Enemy took 20 damage"), record that outcome. After a set number of turns or when the history grows large, call the LLM (or a smaller LLM) in a "summarization mode": provide it with the accumulated history (possibly as text descriptions) and ask for a summary of the important facts so far. Replace the history with this summary (or keep the summary and some recent events for granularity). This summary can then be included in the prompt for future decisions (e.g., "Summary of game so far: [text]"). For example, after a long Pokémon battle, the summary might be: "_Summary: Pikachu defeated two opponents but is low on health; one enemy remains._".

- **Usage in Prompt:** When summarization is enabled, modify the prompt to include the summary or relevant memory. Possibly, structure the system prompt as: _"You are playing [Game]. Here is what has happened so far: [Summary]. Now at the current state (see image), decide the next action."_ The model will then consider that background context when deciding. We will be cautious to not overshoot the model’s context length – the summary should be concise, and we won't include raw history by default (only the summary). In testing, we should verify that including this summary helps the model (e.g., remembering earlier choices or goals). If not needed, we simply disable this feature to streamline the pipeline.

- **R&D Note:** This feature is marked beta because it involves an additional LLM call and the quality of summaries might affect performance. We will implement it such that it can be toggled via a configuration flag. Default configuration will have it off, meaning the model only sees the current frame (and possibly the last action or any on-screen text) without long-term memory. Users can opt-in if they want the AI to handle longer narrative context.

## 7. Timing and Turn Execution Strategy

The system will prioritize **stability in executing actions**, with allowances for game-specific timing:

- **Frame and Input Timing:** After issuing an input to the emulator, it’s crucial to wait until the game has processed that input. For turn-based games, this might mean waiting for an enemy turn or a dialogue to finish. Our approach is to use a **turn loop** rather than a continuous real-time loop. For example, in a Pokémon battle: the AI chooses an attack (presses A on the "Attack" option), then the game will play out the attack animation and the enemy's move before waiting for player input again. We can detect this by either:

  - Monitoring a specific memory address or screen region (advanced, emulator-specific), or
  - A simpler heuristic: after the AI action, call `tick()` or allow frames to advance until a certain condition. For instance, we could keep calling `tick()` in PyBoy until a menu reappears or until a fixed number of frames have passed that usually covers the enemy turn. With mGBA, we might rely on a short sleep or use the `/core/framecount` endpoint ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=6)) to detect progress.  
    A safe default is to introduce a **delay** after each action. Start with a conservative delay (e.g., 1 second or equivalent frames) and adjust per game. This “stability-first” approach ensures we don’t overwhelm the emulator or the model with new frames while the game is still updating from the last move.

- **Game-Specific Adjustments:** Provide a way to override the default delay or frame-skip for specific games:

  - In some games, 1 second might be too long, slowing play unnecessarily. In others, it might be too short (e.g., complex battle animations might take 3-4 seconds). We will calibrate by testing a few turns in each target game and adjusting a parameter (like `action_delay` in seconds or `frames_to_advance` count). These can be stored in a config per game, or determined dynamically (for example, by reading the in-game timer or waiting for a known pixel/color change that signifies the end of an animation).
  - For PyBoy, since we control the frame stepping, we might do `pyboy.tick(n)` to advance n frames in one go ([GitHub - Baekalfen/PyBoy: Game Boy emulator written in Python](https://github.com/Baekalfen/PyBoy#:~:text=for%20_%20in%20range%28target%29%3A%20pyboy)). If we know, say, a move resolution takes ~120 frames, we can do `pyboy.tick(120)` after selecting a move, then capture the screen.
  - For mGBA, which runs in real time by default, we can either rely on time.sleep or use mGBA’s frame count. For example, use `/core/framecount` before and after, and wait until a certain number of frames have advanced. Another idea is to leverage an emulator pause: if mGBA-http allows it, we could step frame by frame manually. However, implementing our own “wait until state changes” logic might be complex; a fixed wait is simpler and robust if chosen properly.

- **Error Handling and Stability:** Ensure to handle cases where the model outputs an invalid action or the emulator doesn’t respond:
  - If the model produces something unrecognized (e.g., long text or a non-action), we can log it and either ignore it or fall back to a default action (like doing nothing or pressing a safe button like "B" to cancel). It's important this doesn’t crash the loop. Possibly re-prompt the model with clearer instructions if this happens frequently.
  - If the emulator fails to execute an input (e.g., mGBA-http returns an error), catch that and attempt a retry. The system should detect if the emulator instance is no longer running and try to reconnect or reset if possible. For development, keeping the emulator open and running continuously is easiest; if it crashes, the agent could attempt to relaunch it (though that involves reloading state).
  - We will also log each turn’s image (maybe save to disk or keep in memory) and the chosen action for debugging. This history can help tune the timing and summarization later.

## 8. Implementation Status and Progress

We've completed the core implementation of the EMU-VLM system with the following components:

### Completed Components ✅

1. **Core Emulator Interfaces:**
   - Created base `GameEmulator` abstract class in `emulators/base.py`
   - Implemented `PyBoyEmulator` for Game Boy/Game Boy Color games in `emulators/pyboy_emulator.py`
   - Implemented `MGBAEmulator` for Game Boy Advance games using mGBA-http in `emulators/mgba_emulator.py`

2. **LLM Agent Implementation:**
   - Built `LLMAgent` class in `model/agent.py` for decision-making
   - Created functions for image processing, prompt construction, and API communication
   - Implemented action parsing logic to map model outputs to emulator inputs
   - Added optional summarization feature to maintain game context

3. **Main Game Loop:**
   - Created the primary game loop in `play_game.py`
   - Added configuration loading from YAML
   - Implemented command-line arguments for game selection and options
   - Built error handling and graceful shutdown

4. **Support Systems:**
   - Created `test_emulators.py` for testing emulator connections
   - Added `start_vllm_server.sh` script to launch the vLLM server
   - Created `config.yaml` for game and model configuration
   - Added `requirements.txt` with all necessary dependencies
   - Built `demo_game.py` for testing with predefined actions
   - Developed `test_model.py` for prompt engineering experiments
   - Implemented `monitor_game.py` with GUI for visualizing gameplay

5. **Documentation:**
   - Updated `README.md` with installation and usage instructions
   - Maintained detailed design document in `PLAN.md`
   - Created `TODO.md` to track project tasks and progress

**Step 2: Set Up Qwen2.5-VL Model via vLLM**  
 2.1. Launch the vLLM server hosting Qwen2.5-VL-3B-Instruct. Confirm it’s accessible (e.g., via an API endpoint or local port). If using a Python-based approach instead, load the model with HuggingFace Transformers (ensuring Qwen2.5-VL is supported ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=Requirements)) ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=and%20Transformers)) and the `qwen-vl-utils` for image handling is installed ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=We%20offer%20a%20toolkit%20to,it%20using%20the%20following%20command))).  
 2.2. **Test the model** with a simple image+prompt input to ensure it works. For example, feed a sample game screenshot and a prompt like "What do you see?" to verify the model is responding sensibly. This validates that the image preprocessing (base64 or file path passing) is correctly set up ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=match%20at%20L279%20%7B,the%20similarities%20between%20these%20images)).

**Step 3: Implement the Emulator Interface Classes**  
 3.1. **PyBoyEmulator class**: Implement initializer to load a ROM with PyBoy. Provide methods: `get_frame()` returning a PIL image (`pyboy.screen_image()`), `press(button)` and `release(button)` mapping to PyBoy’s button controls, and optionally `tick(frames=1)` to advance frames. Also add a method `close()` to stop the emulator (`pyboy.stop()`).  
 3.2. **MGBAEmulator class**: Implement initializer to connect to a running mGBA-http server (store the base URL and maybe verify connection by calling a trivial endpoint like `/core/framecount` ([mGBA-http/docs/Examples.md at main · nikouu/mGBA-http · GitHub](https://github.com/nikouu/mGBA-http/blob/main/docs/Examples.md?ref=nikouusitalo.com#:~:text=6))). Provide `get_frame()`: perform the screenshot POST request to a temp file path, open that file with PIL, return the image. Provide `press(button)`/`release(button)`: send HTTP requests to mGBA for button press/release (or a combined press call if available). Since mGBA may require holding a button for a frame, we might simulate a quick tap by calling press then release after a short delay or next frame. Provide a `close()` to disconnect or shut down (maybe call `/core/quit` if it exists, or simply stop sending commands).  
 3.3. **Game-specific setup**: If needed, create small subclasses or configurations for particular games (e.g., a class for a specific game if it needs special memory checks). Initially, we can treat all GB games the same and all GBA games the same in terms of interface. The difference can be handled via configuration (like which emulator class to use, what buttons are allowed, what delay to use).  
 3.4. **Testing**: Write a short script to instantiate each emulator class and perform a test: load game, get a frame, save it to disk to ensure screenshot works, simulate a button press (like pressing 'Start' to pass the start screen) and tick forward, then get another frame. Do this on each platform to verify cross-platform functionality. For PyBoy, test on macOS specifically to ensure the SDL window opens or headless mode runs.

**Step 4: Develop the LLM Agent Logic**  
 4.1. Create a function to generate the prompt for the model. This might take parameters: the current frame image (we could encode it as needed for the model), an optional summary of history, and maybe the last action or any text from the screen if easily available. The function should return the prompt in the format Qwen expects (likely a list of messages for Qwen, since many vision-language models use a message list input ([Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct#:~:text=match%20at%20L279%20%7B,the%20similarities%20between%20these%20images))). For example, with no history: `[{"type": "image", "image": image_data}, {"type": "text", "text": "You are playing XYZ. What will you do next? Only respond with an action."}]`.  
 4.2. Create a function `query_model(prompt)` that sends this prompt to the vLLM server and returns the raw text output. This might involve an HTTP POST to vLLM’s API. If vLLM provides an OpenAI-compatible API, use the appropriate payload (with perhaps a special way to include images). If not, consider running the model inference in-process by calling the transformers pipeline (this is heavier on the runtime, but simpler for formatting images).  
 4.3. Implement the parsing logic for the model’s response. Keep a list or enum of valid actions for the current game. For instance, if the output contains "up" (case-insensitive), map to `UP` button; if "press A", map to `A` button. Use a simple approach first (multiple if-elif for each action). Also handle special outputs: if the model says something like "There is nothing to do" or produces a long sentence, we might either ignore it or extract a keyword. This part may require iteration to refine prompts so that the model usually replies with concise commands.  
 4.4. **Dry-run the decision loop**: Without hooking to the emulator yet, simulate a cycle by feeding a static image to the model and getting an action. Adjust the prompt until the model reliably returns an action keyword. For example, we may find we need to explicitly say “Answer with one of [Up, Down, Left, Right, A, B] only.” in the user prompt to constrain it.

**Step 5: Main Control Loop Implementation**  
 5.1. Initialize the appropriate emulator class based on the game chosen (we can detect by file extension or a user input). For GB/GBC use PyBoyEmulator; for GBA use MGBAEmulator. Ensure the emulator is loaded and paused if needed at the start (some games start with an intro, so we might press Start to get to a menu or wait for a prompt). Possibly take an initial screenshot and feed it to the model to begin.  
 5.2. Loop structure:

```python
while not game_over:
    frame = emulator.get_frame()
    prompt = make_prompt(frame, history_summary)
    action_text = query_model(prompt)
    action = parse_action(action_text)
    if action is None:
        continue  # or choose a default like "wait"
    emulator.send_input(action)
    apply_post_action_delay(game_config)  # wait or tick some frames
    update_history(action, frame)  # record for optional summary
```

This loop runs until `game_over` is True. Determining game over can be game-specific (e.g., in Pokemon, checking if we reached the "The End" screen or a certain memory flag). For now, we might run for a fixed number of steps or allow manual termination.  
 5.3. Implement `apply_post_action_delay()`. For PyBoy, this could be a call like `pyboy.tick(frames)` with frames determined from config (e.g., 60 frames = 1 second of GB time). For mGBA, use `time.sleep(sec)` or if mGBA-http allows stepping, do multiple `/core/step` calls. Alternatively, call `get_frame()` in a loop until something changes – but image diffing might be unreliable due to animations. A fixed wait is simpler. This value (seconds or frames) can be set in a per-game configuration object (for example, Pokemon might require ~2 seconds after selecting an attack to wait for animations).  
 5.4. `update_history(action, frame)`: If summarization is enabled, collect relevant info. We might extract text from the frame using OCR (Qwen could actually do this: we could have an auxiliary prompt to describe the frame, but that’s double the model usage. Instead, perhaps rely on detecting if certain known events happened. This area could be complex; a simpler way is to feed the model an image and ask "describe what happened" after each turn, but that is heavy. Since it's optional, we can implement a basic approach: maintain a list of actions taken and perhaps certain state variables (if we can read e.g. player HP from memory or screen via pattern). For summarization, it might be enough to store, "_Turn X: used Y move, outcome: [if we can detect faint or win]_". We'll define placeholders and refine as needed. Then after N turns, call Qwen or a text-only model with `"\n".join(history)` asking for a summary.)
5.5. End of loop: how to break. If the game requires an explicit end, we look for conditions. For development, we might run a predetermined number of turns to test. Eventually, we might parse the screen for an end-of-game message or have a manual escape condition (like if the model outputs "quit" or pressing a special key to stop).

**Step 6: Enable Optional Features**  
 6.1. **Summarization Toggle**: Implement a flag (in config or command-line argument) to turn on the summarization. When on, ensure the `history_summary` is included in prompt generation and that the summarization routine triggers periodically. Test with it on to see that the model still behaves (the summary text should not confuse it into ignoring the image).  
 6.2. **Multiple Games Support**: Test the loop with at least one GB/GBC game and one GBA game. Make adjustments in the emulator interface or control loop if any issues arise (for instance, maybe the GBA emulator doesn't update unless unpaused). Also test on at least two OS (macOS and one other, if possible) to validate cross-platform operation. Pay attention on macOS to giving the Python script accessibility permissions if we had to use any GUI automation (we aimed not to, so ideally nothing special is needed).

**Step 7: Documentation and Usage**  
 7.1. Write **README.md** (the user guide) with clear instructions to install and run the system. Include notes for each supported platform (especially any quirks on macOS). Document how to add a new game or emulator. Also, explain the optional summary feature and how to enable it (and caution that it’s experimental).  
 7.2. Write **PLAN.md** (this document) as a developer-oriented guide explaining the design decisions and how to proceed with implementation step by step (done as above).  
 7.3. Verify that README instructions have been followed in a fresh environment to ensure nothing is missing (dependency, step, etc.).

By following this plan, we have successfully built a robust system where a Python AI agent can play turn-based games through emulators, using the Qwen2.5-VL model to interpret game screens and decide actions. The implementation emphasizes clarity (via modular code per emulator/game), stability (timing and error handling), and extensibility (easy to add new games or improve the prompt/summary logic).

## 9. Advanced Features Implementation

We've enhanced the system with several advanced features that improve performance, reliability, and usability:

### 1. Frame Caching System ✅
We've implemented a sophisticated frame caching system to reduce redundant model calls:

- **Image Hashing**: Using MD5 hashing of images to create unique identifiers for frames
- **Similarity Detection**: Computing frame similarity to identify nearly identical screens
- **Action Caching**: Storing model decisions for previously seen frames
- **Configurable Thresholds**: Tunable similarity threshold to balance cache hit rate vs. accuracy
- **Debug Snapshots**: Saving key frames to disk for analysis and debugging

This system dramatically reduces API calls and improves response time, especially for repetitive game screens like menus or battle sequences.

### 2. Session Management ✅
We've added comprehensive session management capabilities:

- **Save/Load System**: Ability to pause and resume games at any point
- **Auto-save**: Configurable auto-save at regular intervals to prevent progress loss
- **State Preservation**: Saving game state, turn count, and context summaries
- **Session Recovery**: Seamless resumption of gameplay from saved points

### 3. Dynamic Timing ✅
We've implemented context-aware timing adjustments:

- **Action-Specific Delays**: Different delays for different action types (navigation, battles, dialogue)
- **Game-Specific Timing**: Custom timing configurations for each game
- **Context Detection**: Determining appropriate delays based on game context

### 4. Enhanced Logging ✅
We've added comprehensive logging and debugging facilities:

- **Structured Logs**: Organized logging with configurable levels
- **Performance Metrics**: Tracking model API call times and cache performance
- **Frame Capture**: Saving frames before and after actions for analysis
- **Directory Structure**: Organized storage of logs, frames, and sessions

## 10. Next Steps and Improvements

After implementing these advanced features, here are the next areas to focus on:

### 1. Testing and Refinement
- **Game Compatibility**: Test the system with more turn-based games to ensure broad compatibility
- **Prompt Engineering**: Refine prompts to get more consistent and accurate actions from the LLM
- **Cache Optimization**: Fine-tune the similarity threshold for optimal cache performance
- **Session Testing**: Verify session save/load functionality across various games

### 2. Additional Enhanced Features
- **Text Box Detection**: Implement computer vision to detect text boxes and menus for better timing
- **Visualization Dashboard**: Create a real-time dashboard for monitoring gameplay and decisions
- **Video Export**: Add ability to generate gameplay videos from saved frame sequences
- **Smart Retry**: Implement intelligent retry logic for failed model actions
- **Game-Specific Prompts**: Create tailored prompts for different game types and contexts

### 3. Extensibility
- **Additional Emulators**: Extend support to more emulators like NES/SNES via RetroArch
- **Plugin Architecture**: Create a plugin system for easier addition of new emulators
- **Alternative VLMs**: Add support for Claude 3 Sonnet and other vision-language models
- **Configuration Tools**: Develop user-friendly tools for game and system configuration

### 4. Community Engagement
- **Example Games**: Create detailed examples and tutorials for popular turn-based games
- **Documentation**: Expand documentation for contributors and users
- **Demonstrations**: Add demo videos and screenshots to showcase the system in action
- **Public Release**: Prepare for a wider release with comprehensive documentation and examples
