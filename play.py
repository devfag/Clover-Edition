from pathlib import Path

# remove this in a few days
with open(Path('interface', 'start-message.txt'), 'r') as file:
    print('\x1B[7m' + file.read() + '\x1B[27m')
import gc
import torch

from getconfig import config
from storymanager import Story
from utils import *
from gpt2generator import GPT2Generator
from interface import instructions

# add color for windows users that install colorama
#   It is not necessary to install colorama on most systems
try:
    import colorama

    colorama.init()
except ModuleNotFoundError:
    pass

logger.info("Colab detected: {}".format(in_colab()))

def get_generator():
    output(
        "\nInitializing AI Engine! (This might take a few minutes)",
        "loading-message", end="\n\n"
    )
    models = [x for x in Path('models').iterdir() if x.is_dir()]
    if not models:
        raise FileNotFoundError(
            'There are no models in the models directory! You must download a pytorch compatible model!')
    elif len(models) > 1:
        output("You have multiple models in your models folder. Please select one to load:", 'message')
        for n, model_path in enumerate(models):
            output("{}: {}".format(n, model_path.name), 'menu')

        model = models[input_number(len(models) - 1)]
    else:
        model = models[0]
        logger.info("Using model: " + str(model))
    return GPT2Generator(
        model_path=model,
        generate_num=settings.getint("generate-num"),
        temperature=settings.getfloat("temp"),
        top_k=settings.getint("top-keks"),
        top_p=settings.getfloat("top-p"),
        repetition_penalty=settings.getfloat("rep-pen"),
    )


if not Path("prompts", "Anime").exists():
    try:
        import pastebin
    except:
        output("Continuing without downloading prompts...", "error")


def d20ify_speech(action, d):
    adjectives_say_d01 = [
        "mumble",
        "prattle",
        "incoherently say",
        "whine",
        "ramble",
        "wheeze",
    ]
    adjectives_say_d20 = [
        "successfully",
        "persuasively",
        "expertly",
        "conclusively",
        "dramatically",
        "adroitly",
        "aptly",
    ]
    if d == 1:
        adjective = random.sample(adjectives_say_d01, 1)[0]
        action = "You " + adjective + " " + action
    elif d == 20:
        adjective = random.sample(adjectives_say_d20, 1)[0]
        action = "You " + adjective + " say " + action
    else:
        action = "You say " + action
    return action


def d20ify_action(action, d):
    adjective_action_d01 = [
        "disastrously",
        "incompetently",
        "dangerously",
        "stupidly",
        "horribly",
        "miserably",
        "sadly",
    ]
    adjective_action_d20 = [
        "successfully",
        "expertly",
        "conclusively",
        "adroitly",
        "aptly",
        "masterfully",
    ]
    if d == 1:
        adjective = random.sample(adjective_action_d01, 1)[
            0
        ]
        action = "You " + adjective + " fail to " + action
    elif d < 5:
        action = "You attempt to " + action
    elif d < 10:
        action = "You try to " + action
    elif d < 15:
        action = "You start to " + action
    elif d < 20:
        action = "You " + action
    else:
        adjective = random.sample(adjective_action_d20, 1)[
            0
        ]
        action = "You " + adjective + " " + action
    return action


def load_prompt(f):
    with f.open('r', encoding="utf-8") as file:
        try:
            lines = file.read().strip().split('\n')
            if len(lines) < 2:
                context = lines[0]
                prompt = ""
            elif len(lines) == 2:
                context = lines[0]
                prompt = lines[1]
            else:
                context = ' '.join(lines[0:-1])
                prompt = lines[-1]
            return context, prompt
        except IOError:
            output("Something went wrong; aborting. ", "error")
    return None, None


def new_story(generator, context, prompt, memory=None, first_result=None):
    if memory is None:
        memory = []
    context = context.strip()
    prompt = prompt.strip()
    story = Story(generator, context, memory)
    if first_result is None:
        story.act(prompt)
    else:
        story.actions.append(prompt)
        story.results.append(first_result)
    story.print_story()
    return story


def save_story(story):
    """Saves the existing story to a json file in the saves directory to be resumed later."""
    savefile = story.savefile if story.savefile else ""
    while True:
        print()
        temp_savefile = input_line("Please enter a name for this save: ", "query")
        savefile = temp_savefile if len(temp_savefile.strip()) > 0 else savefile
        if not savefile or len(savefile.strip()) == 0:
            output("Please enter a valid savefile name. ", "error")
        else:
            break
    savefile = os.path.splitext(remove_prefix(savefile, "saves/").strip())[0]
    story.savefile = savefile
    savedata = story.to_json()
    finalpath = "saves/" + savefile + ".json"
    try:
        os.makedirs(os.path.dirname(finalpath), exist_ok=True)
    except OSError:
        output("Error when creating subdirectory; aborting. ", "error")
    with open(finalpath, 'w') as f:
        try:
            f.write(savedata)
            output("Successfully saved to " + savefile, "message")
        except IOError:
            output("Unable to write to file; aborting. ", "error")


def load_story(f):
    with f.open('r', encoding="utf-8") as file:
        try:
            story = Story(generator, "")
            story.savefile = os.path.splitext(file.name.strip())
            story.from_json(file.read())
            return story, story.context, story.actions[-1] if len(story.actions) > 0 else ""
        except FileNotFoundError:
            output("Save file not found. ", "error")
        except IOError:
            output("Something went wrong; aborting. ", "error")
    return None, None, None


def alter_text(text):
    if use_ptoolkit():
        return edit_multiline(text).strip()

    sentences = sentence_split(text)
    while True:
        output(" ".join(sentences), 'menu')
        list_items(
            [
                "Edit a sentence.",
                "Remove a sentence.",
                "Add a sentence.",
                "Edit entire prompt.",
                "Save and finish."
            ], 'menu')
        try:
            i = input_number(4)
        except:
            continue
        if i == 0:
            while True:
                output("Choose the sentence you want to edit.", "menu")
                list_items(sentences + ["(Back)"], "menu")
                i = input_number(len(sentences))
                if i == len(sentences):
                    break
                else:
                    output(sentences[i], 'menu')
                    res = input_line("Enter the altered sentence: ", 'menu').strip()
                    if len(res) == 0:
                        output("Invalid sentence entered: returning to previous menu. ", 'error')
                        continue
                    sentences[i] = res
        elif i == 1:
            while True:
                output("Choose the sentence you want to remove.", "menu")
                list_items(sentences + ["(Back)"], "menu")
                i = input_number(len(sentences))
                if i == len(sentences):
                    break
                else:
                    del sentences[i]
        elif i == 2:
            while True:
                output("Choose the sentence you want to insert after.", "menu")
                list_items(["(Beginning)"] + sentences + ["(Back)"], "menu")
                max = len(sentences) + 1
                i = input_number(max)
                if i == max:
                    break
                else:
                    res = input_line("Enter the new sentence: ", 'menu').strip()
                    if len(res) == 0:
                        output("Invalid sentence entered: returning to previous menu. ", 'error')
                        continue
                    sentences.insert(i, res)
        elif i == 3:
            output(" ".join(sentences), 'menu')
            res = input_line("Enter the new altered prompt: ", 'menu').strip()
            if len(res) == 0:
                output("Invalid prompt entered: returning to previous menu. ", 'error')
                continue
            text = res
            sentences = sentence_split(res)
        elif i == 4:
            break
    return " ".join(sentences).strip()


def play(generator):
    print()

    with open(Path("interface", "mainTitle.txt"), "r", encoding="utf-8") as file:
        output(file.read(), "title", wrap=False, beg='')

    with open(Path("interface", "subTitle.txt"), "r", encoding="utf-8") as file:
        cols = termWidth
        for line in file:
            line=re.sub(r'\n', '', line)
            line=line[:cols]
            #fills in the graphic using reverse video mode substituted into the areas between |'s
            if use_ptoolkit():
                style = Style.from_dict({
                    'nor': ptcolors['subtitle'],
                    'rev': ptcolors['subtitle'] + ' reverse',
                })
                text = re.sub(r'\|[ _]*(\||$)', lambda x: '<rev>'+x.group(0)+'</rev>', line)
                print_formatted_text(HTML('<nor>' + text + '</nor>'), style=style)
            else:
                output(re.sub(r'\|[ _]*(\||$)', lambda x: '\x1B[7m' + x.group(0) + '\x1B[27m', line), 'subtitle',
                       wrap=False, beg='')

    output("Go to https://github.com/cloveranon/Clover-Edition/ "
           "or email cloveranon@nuke.africa for bug reports, help, and feature requests.",
           'subsubtitle')

    # Prevent reference before assignment
    story = None
    context = None
    prompt = None

    while True:
        # May be needed to avoid out of mem
        gc.collect()
        torch.cuda.empty_cache()

        list_items(["Pick Prompt From File (Default if you type nothing)", "Write Custom Prompt", "Load a Saved Game"],
                   'menu')
        new_game_option = input_number(2)

        if new_game_option == 0:
            prompt_file = select_file(Path("prompts"), ".txt")
            if prompt_file:
                context, prompt = load_prompt(prompt_file)
            else:
                continue
        elif new_game_option == 1:
            with open(
                    Path("interface", "prompt-instructions.txt"), "r", encoding="utf-8"
            ) as file:
                output(file.read(), "instructions", wrap=False)
            if use_ptoolkit():
                output("Context>", "main-prompt")
                context = edit_multiline()
                output("Prompt>", "main-prompt")
                prompt = edit_multiline()
            else:
                context = input_line("Context> ", "main-prompt")
                prompt = input_line("Prompt> ", "main-prompt")
            filename = input_line("Name to save prompt as? (Leave blank for no save): ", "query")
            filename = re.sub("-$", "", re.sub("^-", "", re.sub("[^a-zA-Z0-9_-]+", "-", filename)))
            if filename != "":
                try:
                    with open(
                            Path("prompts", filename + ".txt"), "w", encoding="utf-8"
                    ) as f:
                        f.write(context + "\n" + prompt)
                except IOError:
                    output("Permission error! Unable to save custom prompt. ", "error")
        elif new_game_option == 2:
            story_file = select_file(Path("saves"), ".json")
            if story_file:
                story, context, prompt = load_story(story_file)
                if not story:
                    continue
            else:
                continue

        if len((context + prompt).strip()) == 0:
            output("Story has no prompt or context. Please enter a valid custom prompt. ", "error")
            continue

        instructions()

        if story is None:
            output("Generating story...", "loading-message")
            story = new_story(generator, context, prompt)
        else:
            output("Loading story...", "loading-message")
            story.print_story()

        while True:
            # Generate suggested actions
            act_alts = settings.getint("action-sugg")
            if act_alts > 0:
                # TODO change this to two messages for different colors
                suggested_actions = []
                output("Suggested actions:", "selection-value")
                action_suggestion_lines = 2
                for i in range(act_alts):
                    suggested_action = story.get_suggestion()
                    if len(suggested_action.strip()) > 0:
                        j = len(suggested_actions)
                        suggested_actions.append(suggested_action)
                        suggestion = "{}) {}".format(j, suggested_action)
                        action_suggestion_lines += \
                            output(suggestion, "selection-value", beg='' if i != 0 else None)

            bell()
            print()

            if use_ptoolkit():
                action = input_line("> ", "main-prompt", default="%s" % "You ")
            else:
                action = input_line("> You ", "main-prompt")

            # Clear suggestions and user input
            if act_alts > 0:
                action_suggestion_lines += 2
                if not IN_COLAB:
                    clear_lines(action_suggestion_lines)

            # Users can type in "/command", or "You /command" if prompt_toolkit is on and they left the "You" in
            cmd_regex = re.search(r"^(?: *you *)?/([^ ]+) *(.*)$", action, flags=re.IGNORECASE)

            # If this is a command
            if cmd_regex:
                action = cmd_regex.group(1).strip().lower()
                cmd_args = cmd_regex.group(2).strip().split()
                if action == "set":
                    if len(cmd_args) < 2:
                        output("Invalid number of arguments for set command. ", "error")
                        instructions()
                        continue
                    if cmd_args[0] in settings:
                        curr_setting_val = settings[cmd_args[0]]
                        output(
                            "Current Value of {}: {}     Changing to: {}".format(
                                cmd_args[0], curr_setting_val, cmd_args[1]
                            )
                        )
                        settings[cmd_args[0]] = cmd_args[1]
                        output("Saving an invalid option will corrupt file! ", "error")
                        if input_bool("Save setting? (y/N): ", "selection-prompt"):
                            try:
                                with open("config.ini", "w", encoding="utf-8") as file:
                                    config.write(file)
                            except IOError:
                                output("Permission error! Changes will not be saved for next session.", "error")
                    else:
                        output("Invalid setting", "error")
                        instructions()

                elif action == "menu":
                    if input_bool("Do you want to save? (y/N): ", "query", "user-text"):
                        save_story(story)
                    story = None
                    context = None
                    prompt = None
                    break

                elif action == "restart":
                    output("Restarting story...", "loading-message")
                    if len((context + prompt).strip()) == 0:
                        output("Story has no prompt or context. Please enter a valid prompt. ", "error")
                        continue
                    story = new_story(generator, story.context, prompt)

                elif action == "quit":
                    if input_bool("Do you want to save? (y/N): ", "query", "user-text"):
                        save_story(story)
                    exit()

                elif action == "help":
                    instructions()

                elif action == "print":
                    use_wrap = input_bool("Print with wrapping? (y/N): ", "query", "user-text")
                    use_color = input_bool("Print with colors? (y/N): ", "query", "user-text")
                    output("Printing story...", "message")
                    story.print_story(wrap=use_wrap, color=use_color)

                elif action == "retry":
                    if len(story.actions) < 2:
                        output("Restarting story...", "loading-message")
                        if len((context + prompt).strip()) == 0:
                            output("Story has no prompt or context. Please enter a valid prompt. ", "error")
                            continue
                        story = new_story(generator, story.context, prompt)
                        continue
                    else:
                        new_action = story.actions[-1]
                        story.revert()
                        result = story.act(new_action)
                        if story.is_looping():
                            story.revert()
                            output("That action caused the model to start looping. Try something else instead. ",
                                   "error")
                            continue
                        story.print_last()

                elif action == "revert":
                    if len(story.actions) < 2:
                        output("You can't go back any farther. ", "error")
                        continue
                    story.revert()
                    output("Last action reverted. ", "message")
                    story.print_last()

                elif action == "alter":
                    story.results[-1] = alter_text(story.results[-1])
                    story.print_last()

                elif action == "context":
                    story.context = alter_text(story.context)
                    story.print_last()

                elif action == "remember":
                    memory = cmd_regex.group(2).strip()
                    if len(memory) > 0:
                        memory = re.sub("^[Tt]hat +(.*)", "\\1", memory)
                        memory = memory.strip('.')
                        memory = memory.strip('!')
                        memory = memory.strip('?')
                        story.memory.append(memory[0].upper() + memory[1:] + ".")
                        output("You remember " + memory + ". ", "message")
                    else:
                        output("Please enter something valid to remember. ", "error")

                elif action == "forget":
                    while True:
                        i = 0
                        output("Select a memory to forget: ", "menu")
                        list_items(story.memory + ["(Finish)"], "menu")
                        i = input_number(len(story.memory))
                        if i == len(story.memory):
                            break
                        else:
                            del story.memory[i]

                elif action == "save":
                    save_story(story)

                elif action == "load":
                    story_file = select_file(Path("saves"), ".json")
                    if story_file:
                        tstory, tcontext, tprompt = load_story(story_file)
                        if tstory:
                            output("Loading story...", "message")
                            story = tstory
                            context = tcontext
                            prompt = tprompt
                            story.print_story()
                        else:
                            story.print_last()
                    else:
                        story.print_last()

                elif action == "summarize":
                    first_result = story.results[-1]
                    output(story.context, "user-text", "(YOUR SUMMARY HERE)", "message")
                    output(story.results[-1], "ai-text")
                    new_prompt = input_line("Enter the summary for the new story: ", "query")
                    new_prompt = format_result(new_prompt)
                    if len(new_prompt) == 0:
                        output("Invalid new prompt; cancelling. ", "error")
                        story.print_last()
                        continue
                    if input_bool("Do you want to save your previous story? (y/N): ",
                                  "query", "user-text"):
                        save_story(story)
                    story = new_story(generator, context, new_prompt, memory=story.memory, first_result=first_result)

                else:
                    output("Invalid command: " + action, "error")

            # Otherwise this is just a normal action.
            else:
                action = format_result(action)

                story_insert_regex = re.search("^ *(?:you)? *! *(.*)$", action, flags=re.IGNORECASE)

                # If the player enters a story insert.
                if story_insert_regex:
                    action = story_insert_regex.group(1)
                    if not action or len(action.strip()) == 0:
                        output("Invalid story insert. ", "error")
                        continue
                    output(format_result(action), "user-text")

                # If the player enters a real action
                elif action != "":
                    # Roll a die. We'll use it later if action-d20 is enabled.
                    d = random.randint(1, 20)
                    logger.debug("roll d20=%s", d)

                    # Add the "you" if it's not prompt-toolkit
                    if not settings.getboolean("prompt-toolkit"):
                        action = re.sub("^ *(?:you)? *(?! *you)(.+)$", "You \\1", action, flags=re.IGNORECASE)

                    sugg_action_regex = re.search(r"^ *(?:you)? *([0-9]+)$", action, flags=re.IGNORECASE)
                    user_speech_regex = re.search(r"^ *you *say *([\"'].*[\"'])$", action, flags=re.IGNORECASE)
                    user_action_regex = re.search(r"^ *you *(.+)$", action, flags=re.IGNORECASE)

                    if sugg_action_regex:
                        action = sugg_action_regex.group(1)
                        if action in [str(i) for i in range(len(suggested_actions))]:
                            action = "You " + suggested_actions[int(action)].strip()

                    if user_speech_regex:
                        action = user_speech_regex.group(1)
                        if settings.getboolean("action-d20"):
                            action = d20ify_speech(action, d)
                        else:
                            action = "You say " + action

                    elif user_action_regex:
                        action = first_to_second_person(user_action_regex.group(1))
                        if settings.getboolean("action-d20"):
                            action = d20ify_action(action, d)
                        else:
                            action = "You " + action

                    if action[-1] not in [".", "?", "!"]:
                        action = action + "."

                    # If the user enters nothing but leaves "you", treat it like an empty action (continue)
                    if re.match(r"^ *you *[.?!]? *$", action, flags=re.IGNORECASE):
                        action = ""

                    # Prompt the user with the formatted action
                    output("> " + format_result(action), "transformed-user-text")

                result = story.act(action)

                # Check for loops
                if story.is_looping():
                    story.revert()
                    output("That action caused the model to start looping. Try something else instead. ",
                           "error")

                # If the player won, ask them if they want to continue or not.
                if player_won(result):
                    output(result, "ai-text")
                    output("YOU WON. CONGRATULATIONS", "message")
                    list_items(["Start a New Game", "\"I'm not done yet!\" (If you still want to play)"])
                    choice = input_number(1)
                    if choice == 0:
                        story = None
                        context = None
                        prompt = None
                        break
                    else:
                        output("Sorry about that...where were we?", "query")

                # If the player lost, ask them if they want to continue or not.
                elif player_died(result):
                    output(result, "ai-text")
                    output("YOU DIED. GAME OVER", "message")
                    list_items(["Start a New Game", "\"I'm not dead yet!\" (If you didn't actually die)"])
                    choice = input_number(1)
                    if choice == 0:
                        story = None
                        context = None
                        prompt = None
                        break
                    else:
                        output("Sorry about that...where were we?", "query")

                # Output the AI's result.
                output(result, "ai-text")


# This is here for rapid development, without reloading the model. You import play into a jupyternotebook with autoreload
if __name__ == "__main__":
    with open(Path("interface", "clover"), "r", encoding="utf-8") as file:
        print(file.read())
    generator = get_generator()
    play(generator)
