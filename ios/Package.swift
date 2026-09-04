// swift-tools-version: 6.0
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "NOVAiOS",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "NOVAiOS",
            targets: ["NOVAiOS"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "NOVAiOS",
            path: "NOVA"
        ),
    ]
)
