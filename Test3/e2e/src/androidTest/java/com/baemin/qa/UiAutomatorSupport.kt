package com.baemin.qa

import androidx.test.uiautomator.BySelector
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import java.io.ByteArrayOutputStream

object Timeouts {
    const val SCREEN = 10_000L
    const val TRANSITION = 15_000L
    const val PAYMENT = 30_000L
}

fun UiDevice.requireObject(
    selector: BySelector,
    timeoutMs: Long,
    description: String,
): UiObject2 {
    return wait(Until.findObject(selector), timeoutMs)
        ?: throw AssertionError(
            "Timed out after ${timeoutMs}ms waiting for $description.\\n" +
                "Current UI hierarchy:\\n${dumpHierarchy()}",
        )
}

fun UiDevice.requireCondition(
    selector: BySelector,
    timeoutMs: Long,
    description: String,
) {
    if (!wait(Until.hasObject(selector), timeoutMs)) {
        throw AssertionError(
            "Timed out after ${timeoutMs}ms waiting for $description.\\n" +
                "Current UI hierarchy:\\n${dumpHierarchy()}",
        )
    }
}

fun UiObject2.requireEnabled(description: String): UiObject2 {
    check(isEnabled) { "$description is visible but disabled" }
    return this
}

fun UiDevice.dumpHierarchy(): String {
    return runCatching {
        ByteArrayOutputStream().use { output ->
            dumpWindowHierarchy(output)
            output.toString(Charsets.UTF_8.name())
        }
    }.getOrElse { error -> "Unable to dump UI hierarchy: ${error.message}" }
}
