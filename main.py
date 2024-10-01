import sys
import os
import time
from PyObjCTools import AppHelper
from Cocoa import (
    NSApplication,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSObject,
    NSMenu,
    NSMenuItem,
    NSTimer,
    NSDate,
    NSAlert,
    NSTextField,
    NSModalResponseOK,
)

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.done_items = []  # Track done tasks by name

        # Initialize pause state
        self.is_paused = False
        self.pause_time = None
        self.total_paused_time = 0.0

        # Status bar
        status_bar = NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)

        # Create a menu
        self.menu = NSMenu.alloc().init()

        # Read tasks from file
        self.title, self.todo_menu_items = self.read_file()

        # Initialize current_task to the first uncompleted task
        self.current_item_index = self.get_next_uncompleted_task_index()
        if self.current_item_index is not None:
            self.current_task = self.todo_menu_items[self.current_item_index]
        else:
            self.current_task = None

        # **Initialize Pause/Resume Menu Item First**
        self.pause_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Pause", "togglePause:", ""
        )

        # **Now Update Menu Items**
        self.update_menu_items()

        # Attach the menu to the status item
        self.status_item.setMenu_(self.menu)

        self.start_time = time.time()
        # Update the status bar item's title

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, "updateTimer:", None, True
        )

        self.title_update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "updateTitleAndMenuItems:", None, True
        )

    def get_next_uncompleted_task_index(self):
        for idx, task in enumerate(self.todo_menu_items):
            if not any(done.startswith(task) for done in self.done_items):
                return idx
        return None  # All tasks are done

    def updateTimer_(self, timer):
        if self.is_paused:
            return  # Do not update elapsed time if paused

        current_time = time.time()
        elapsed_time = current_time - self.start_time - self.total_paused_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, remainder = divmod(remainder, 60)
        seconds, milliseconds = divmod(remainder, 1)
        milliseconds = int(milliseconds * 1000)

        # Format the time as hh:mm:ss.ms
        time_string = "%02d:%02d:%02d.%03d" % (
            int(hours),
            int(minutes),
            int(seconds),
            milliseconds,
        )

        # Get the current active subtask
        if self.current_item_index is not None and self.current_item_index < len(self.todo_menu_items):
            current_subtask = self.todo_menu_items[self.current_item_index]
        else:
            current_subtask = "All Tasks Completed"

        # Set maximum lengths
        max_title_length = 15  # Adjust as needed
        max_subtask_length = 15  # Adjust as needed

        # Truncate the title if necessary
        truncated_title = (self.title[:max_title_length] + '...') if len(self.title) > max_title_length else self.title

        # Truncate the current subtask if necessary
        truncated_subtask = (current_subtask[:max_subtask_length] + '...') if len(
            current_subtask) > max_subtask_length else current_subtask

        # Combine time string, vertical bar, truncated title, and truncated current subtask
        status_title = f"{time_string} | {truncated_title} | {truncated_subtask}"

        # Update the status bar item's title
        self.status_item.setTitle_(status_title)

        # Set the tooltip to display full title and subtask
        full_status = f"{time_string} | {self.title} | {current_subtask}"
        self.status_item.setToolTip_(full_status)

    def read_file(self):
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        todo_file_path = os.path.join(script_dir, "todolist.txt")
        title = "No Title"
        menu_items = []
        try:
            with open(todo_file_path, "r") as file:
                lines = file.readlines()
                if not lines:
                    return title, menu_items
                title = lines[0].strip()
                # Read subsequent lines until the end or a line that isn't indented
                for line in lines[1:]:
                    if line.startswith('\t') or line.startswith('    '):
                        # Remove leading whitespace and newline characters
                        item = line.strip()
                        if item:
                            menu_items.append(item)
                    else:
                        # Stop reading if the line isn't indented
                        break
            return title if title else "No Title", menu_items
        except FileNotFoundError:
            return "No Title", []  # Ensure both title and menu_items are returned
        except Exception as e:
            # Handle other potential exceptions
            print(f"Error reading 'todolist.txt': {e}")
            return "No Title", []  # Ensure both title and menu_items are returned

    def updateTitleAndMenuItems_(self, timer):
        # Read the updated title and menu items
        self.title, self.todo_menu_items = self.read_file()

        # Update the current_item_index based on the first uncompleted task
        self.current_item_index = self.get_next_uncompleted_task_index()
        if self.current_item_index is not None:
            self.current_task = self.todo_menu_items[self.current_item_index]
        else:
            self.current_task = None

        # Update the menu items
        self.update_menu_items()

    def update_menu_items(self):
        # Clear the menu
        self.menu.removeAllItems()

        # Add the "Next" menu item
        next_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Next", "nextItem:", ""
        )

        if self.current_item_index is None or self.current_item_index >= len(self.todo_menu_items):
            next_item.setEnabled_(False)
        self.menu.addItem_(next_item)

        # Add updated todo items to the menu
        for task in self.todo_menu_items:
            # Check if this task is marked as done
            done_entry = next((done for done in self.done_items if done.startswith(task)), None)
            if done_entry:
                # Display the done version
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    done_entry, "", ""
                )
            else:
                # Display the pending task
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    task, "", ""
                )

            self.menu.addItem_(menu_item)

        # Add a separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # **Add Pause/Resume menu item**
        self.menu.addItem_(self.pause_menu_item)

        # Add another separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Add a "Quit" menu item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "terminate:", ""
        )
        self.menu.addItem_(quit_item)

    def nextItem_(self, sender):
        if self.current_item_index is not None and self.current_item_index < len(self.todo_menu_items):
            # Get the current time snapshot
            current_time = time.time()
            elapsed_time = current_time - self.start_time - self.total_paused_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, remainder = divmod(remainder, 60)
            seconds, milliseconds = divmod(remainder, 1)
            milliseconds = int(milliseconds * 1000)

            # Format the time as hh:mm:ss.ms
            time_string = "%02d:%02d:%02d.%03d" % (
                int(hours),
                int(minutes),
                int(seconds),
                milliseconds,
            )

            # Mark the current task as done
            current_task = self.todo_menu_items[self.current_item_index]
            done_entry = f"{current_task} | DONE | {time_string}"
            self.done_items.append(done_entry)  # Append to list instead of dict

            # Find the next uncompleted task
            self.current_item_index = self.get_next_uncompleted_task_index()
            if self.current_item_index is not None:
                self.current_task = self.todo_menu_items[self.current_item_index]
            else:
                self.current_task = None

            # Update the menu items to reflect the change
            self.update_menu_items()
        else:
            # All items are done; disable the "Next" button
            sender.setEnabled_(False)

    def togglePause_(self, sender):
        if not self.is_paused:
            # Pause the timer
            self.is_paused = True
            self.pause_time = time.time()
            self.timer.invalidate()
            self.pause_menu_item.setTitle_("Resume")
        else:
            # Resume the timer
            self.is_paused = False
            if self.pause_time:
                paused_duration = time.time() - self.pause_time
                self.total_paused_time += paused_duration
                self.pause_time = None
            # Restart the timer
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.05, self, "updateTimer:", None, True
            )
            self.pause_menu_item.setTitle_("Pause")

    def applicationWillTerminate_(self, notification):
        # Invalidate the timers when the application is about to quit
        self.timer.invalidate()
        self.title_update_timer.invalidate()


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
