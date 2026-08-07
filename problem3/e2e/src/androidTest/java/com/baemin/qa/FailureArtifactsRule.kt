package com.baemin.qa

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.junit.rules.TestWatcher
import org.junit.runner.Description
import java.io.File

class FailureArtifactsRule : TestWatcher() {
    override fun failed(error: Throwable, description: Description) {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val device = UiDevice.getInstance(instrumentation)
        val artifactRoot = instrumentation.targetContext
            .getExternalFilesDir("test-artifacts")
            ?: return
        val testDirectory = File(
            artifactRoot,
            description.displayName.replace(Regex("[^A-Za-z0-9._-]"), "_"),
        ).apply { mkdirs() }

        runCatching {
            device.takeScreenshot(File(testDirectory, "failure.png"))
        }
        runCatching {
            device.dumpWindowHierarchy(File(testDirectory, "window.xml"))
        }
        runCatching {
            File(testDirectory, "failure.txt").writeText(
                buildString {
                    appendLine(error::class.java.name)
                    appendLine(error.message.orEmpty())
                    appendLine()
                    appendLine(error.stackTraceToString())
                },
            )
        }
    }
}
