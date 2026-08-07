package com.baemin.qa.pages

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.Timeouts
import com.baemin.qa.requireCondition
import com.baemin.qa.requireEnabled
import com.baemin.qa.requireObject

private const val APP_PACKAGE = "com.baemin.app"

class ShopListPage(private val device: UiDevice) {
    private val screen = By.res(APP_PACKAGE, "shop_list")

    fun waitUntilLoaded(): ShopListPage = apply {
        device.requireCondition(screen, Timeouts.SCREEN, "shop list screen")
    }

    fun openShop(shopName: String) {
        val shopCard = By.res(APP_PACKAGE, "shop_card")
            .hasDescendant(By.text(shopName))
        device.requireObject(shopCard, Timeouts.SCREEN, "shop card '$shopName'")
            .requireEnabled("shop card '$shopName'")
            .click()
        device.requireCondition(
            By.res(APP_PACKAGE, "menu_list"),
            Timeouts.TRANSITION,
            "menu screen after selecting '$shopName'",
        )
    }
}

class MenuPage(private val device: UiDevice) {
    private val screen = By.res(APP_PACKAGE, "menu_list")

    fun waitUntilLoaded(): MenuPage = apply {
        device.requireCondition(screen, Timeouts.SCREEN, "menu list screen")
    }

    fun addMenu(menuName: String) {
        val menuCard = By.res(APP_PACKAGE, "menu_card")
            .hasDescendant(By.text(menuName))
        device.requireObject(menuCard, Timeouts.SCREEN, "menu card '$menuName'")
            .requireEnabled("menu card '$menuName'")
            .click()

        device.requireCondition(
            By.res(APP_PACKAGE, "cart_order_button"),
            Timeouts.TRANSITION,
            "cart screen after selecting '$menuName'",
        )
    }
}

class CartPage(private val device: UiDevice) {
    private val orderButton = By.res(APP_PACKAGE, "cart_order_button")

    fun waitUntilLoaded(): CartPage = apply {
        device.requireCondition(orderButton, Timeouts.SCREEN, "cart order button")
    }

    fun assertSelectedMenu(menuName: String): CartPage = apply {
        val selectedMenu = By.res(APP_PACKAGE, "cart_menu_name").text(menuName)
        device.requireCondition(
            selectedMenu,
            Timeouts.SCREEN,
            "selected menu '$menuName' in cart",
        )
    }

    fun placeOrder() {
        device.requireObject(orderButton, Timeouts.SCREEN, "cart order button")
            .requireEnabled("cart order button")
            .click()
        device.requireCondition(
            By.res(APP_PACKAGE, "payment_button"),
            Timeouts.TRANSITION,
            "payment screen",
        )
    }
}

class PaymentPage(private val device: UiDevice) {
    private val paymentButton = By.res(APP_PACKAGE, "payment_button")

    fun waitUntilLoaded(): PaymentPage = apply {
        device.requireCondition(paymentButton, Timeouts.SCREEN, "payment button")
    }

    fun pay(): String {
        device.requireObject(paymentButton, Timeouts.SCREEN, "payment button")
            .requireEnabled("payment button")
            .click()

        device.requireCondition(
            By.res(APP_PACKAGE, "order_status_screen"),
            Timeouts.PAYMENT,
            "order status screen after payment",
        )

        val orderIdText = device.requireObject(
            By.res(APP_PACKAGE, "order_id"),
            Timeouts.SCREEN,
            "order id",
        ).text
        check(orderIdText.isNotBlank()) { "Order id must not be blank" }
        return orderIdText
    }
}

class OrderStatusPage(private val device: UiDevice) {
    private val screen = By.res(APP_PACKAGE, "order_status_screen")

    fun waitUntilLoaded(): OrderStatusPage = apply {
        device.requireCondition(screen, Timeouts.SCREEN, "order status screen")
    }

    fun assertOrderId(expectedOrderId: String): OrderStatusPage = apply {
        device.requireCondition(
            By.res(APP_PACKAGE, "order_id").text(expectedOrderId),
            Timeouts.SCREEN,
            "order id '$expectedOrderId'",
        )
    }

    fun assertStatus(expectedStatus: String): OrderStatusPage = apply {
        device.requireCondition(
            By.res(APP_PACKAGE, "order_status_text").text(expectedStatus),
            Timeouts.TRANSITION,
            "order status '$expectedStatus'",
        )
    }

    fun assertPaymentCompleted(): OrderStatusPage = apply {
        device.requireCondition(
            By.res(APP_PACKAGE, "payment_status").text("결제 완료"),
            Timeouts.SCREEN,
            "completed payment status",
        )
    }

    fun assertNoBlockingError(): OrderStatusPage = apply {
        val blockingError = By.res(APP_PACKAGE, "blocking_error")
        check(!device.hasObject(blockingError)) {
            "Blocking error is displayed on the order status screen"
        }
    }
}
