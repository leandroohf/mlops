FROM astrocrpublic.azurecr.io/runtime:3.0-11


USER root

# Modern Rust (cargo) via rustup so it understands Cargo.lock v4
# -y to skip prompts; install to /usr/local/rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# optional sanity checks during build (can remove later)
RUN rustc --version && cargo --version

USER astro