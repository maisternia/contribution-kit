#!/usr/bin/env Rscript

# Write the R reference values for every case in effect_size_cases.csv to
# r_effect_size_values.json. Run from the repository root:
#
#   Rscript tests/reference/generate_effect_size_baselines.R
#
# then merge with the high-precision odds-ratio reference:
#
#   python tests/reference/generate_effect_size_baselines.py
#
# Tables are (a, b, c, d) = (group A mismatches, group A matches,
# group B mismatches, group B matches); every ratio is group A versus group B.

suppressPackageStartupMessages({
  library(jsonlite)
  library(PropCIs)
  library(exact2x2)
  library(epitools)
  library(DescTools)
  library(contingencytables)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1) {
  stop("run this script with Rscript")
}
root_dir <- dirname(normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE))
cases_path <- file.path(root_dir, "effect_size_cases.csv")
out_path <- file.path(root_dir, "r_effect_size_values.json")

options(warn = 1)
conf_level <- 0.95
rows <- read.csv(cases_path, stringsAsFactors = FALSE)
# Doubles, not integers: riskscoreci's cubic overflows R's 32-bit integers on
# large tables and silently returns NA.
for (col in c("a", "b", "c", "d")) rows[[col]] <- as.numeric(rows[[col]])

num <- function(x) {
  x <- as.numeric(x)
  if (length(x) != 1 || is.na(x)) {
    return(NULL)
  }
  if (is.infinite(x)) {
    return(if (x > 0) "inf" else "-inf")
  }
  x
}

# Silence one expected warning by message pattern; anything else still prints.
muffle <- function(expr, pattern) {
  withCallingHandlers(expr, warning = function(w) {
    if (grepl(pattern, conditionMessage(w))) invokeRestart("muffleWarning")
  })
}

interval <- function(value, low, high) {
  list(value = num(value), ci_low = num(low), ci_high = num(high))
}

raw_risk_ratio <- function(a, b, c, d) (a / (a + b)) / (c / (c + d))
raw_odds_ratio <- function(a, b, c, d) (a * d) / (b * c)

koopman <- function(a, b, c, d) {
  # When a group has every row mismatched, riskscoreci evaluates its cubic
  # (acos -> NaN) before switching to its iterative branch, whose result it
  # returns; the NaN is discarded.
  ci <- muffle(
    PropCIs::riskscoreci(a, a + b, c, c + d, conf.level = conf_level)$conf.int,
    "NaNs produced"
  )
  interval(raw_risk_ratio(a, b, c, d), ci[1], ci[2])
}

# epitools wants the reference group in row 1 and the event in column 2.
katz <- function(a, b, c, d) {
  if (min(a, b, c, d) == 0) {
    return(interval(raw_risk_ratio(a, b, c, d), NA, NA))
  }
  tab <- rbind(c(d, c), c(b, a))
  est <- suppressWarnings(epitools::riskratio.wald(tab, conf.level = conf_level)$measure[2, ])
  interval(est[[1]], est[[2]], est[[3]])
}

# Haldane-Anscombe as the kit and the manuscripts define it: 0.5 added to every
# cell. DescTools' own correction = TRUE adds it only when a cell is zero.
haldane_anscombe <- function(a, b, c, d) {
  tab <- matrix(c(a, b, c, d), nrow = 2, byrow = TRUE) + 0.5
  est <- DescTools::OddsRatio(tab, method = "wald", conf.level = conf_level)
  interval(est[[1]], est[[2]], est[[3]])
}

exact_or <- function(a, b, c, d, tsmethod) {
  if ((a + c) == 0 || (b + d) == 0) {
    return(NULL)
  }
  tab <- matrix(c(a, b, c, d), nrow = 2, byrow = TRUE)
  # A tight tol makes exact2x2 warn that pnhyper may not be that accurate;
  # these values are only cross-checks against the high-precision reference.
  fit <- muffle(
    exact2x2::exact2x2(tab, conf.level = conf_level, tsmethod = tsmethod, tol = 1e-10),
    "tol set very small"
  )
  interval(raw_odds_ratio(a, b, c, d), fit$conf.int[[1]], fit$conf.int[[2]])
}

# Cross-check only: contingencytables 3.1.0 defines one internal
# calculate_limit for both its exact and mid-p Baptista-Pike functions, so only
# the mid-p function is trustworthy, and it searches theta in [1e-5, 1e5] with
# an absolute uniroot tolerance. Cases where it fails are recorded as null.
midp_or <- function(a, b, c, d) {
  if ((a + c) == 0 || (b + d) == 0) {
    return(NULL)
  }
  tab <- matrix(c(a, b, c, d), nrow = 2, byrow = TRUE)
  fit <- tryCatch(
    suppressWarnings(contingencytables::BaptistaPike_midP_CI_2x2(tab, alpha = 1 - conf_level)),
    error = function(e) NULL
  )
  if (is.null(fit)) {
    return(NULL)
  }
  interval(raw_odds_ratio(a, b, c, d), fit$lower, fit$upper)
}

cases <- lapply(seq_len(nrow(rows)), function(i) {
  a <- rows$a[[i]]
  b <- rows$b[[i]]
  c <- rows$c[[i]]
  d <- rows$d[[i]]
  list(
    set = rows$set[[i]],
    label = rows$label[[i]],
    a = a,
    b = b,
    c = c,
    d = d,
    koopman = koopman(a, b, c, d),
    katz = katz(a, b, c, d),
    haldane_anscombe = haldane_anscombe(a, b, c, d),
    exact2x2_minlike = exact_or(a, b, c, d, "minlike"),
    exact2x2_central = exact_or(a, b, c, d, "central"),
    contingencytables_midp = midp_or(a, b, c, d)
  )
})

versions <- list(
  R = paste(R.version$major, R.version$minor, sep = "."),
  PropCIs = as.character(utils::packageVersion("PropCIs")),
  exact2x2 = as.character(utils::packageVersion("exact2x2")),
  epitools = as.character(utils::packageVersion("epitools")),
  DescTools = as.character(utils::packageVersion("DescTools")),
  contingencytables = as.character(utils::packageVersion("contingencytables"))
)

calls <- list(
  koopman = "PropCIs::riskscoreci(a, a + b, c, c + d, conf.level = 0.95)",
  katz = "epitools::riskratio.wald(rbind(c(d, c), c(b, a)), conf.level = 0.95)$measure[2, ]",
  haldane_anscombe = "DescTools::OddsRatio(matrix(c(a, b, c, d), 2, byrow = TRUE) + 0.5, method = 'wald', conf.level = 0.95)",
  exact2x2_minlike = "exact2x2::exact2x2(matrix(c(a, b, c, d), 2, byrow = TRUE), tsmethod = 'minlike', tol = 1e-10)",
  exact2x2_central = "exact2x2::exact2x2(matrix(c(a, b, c, d), 2, byrow = TRUE), tsmethod = 'central', tol = 1e-10)",
  contingencytables_midp = "contingencytables::BaptistaPike_midP_CI_2x2(matrix(c(a, b, c, d), 2, byrow = TRUE), alpha = 0.05)"
)

out <- list(
  provenance = list(
    generator = "tests/reference/generate_effect_size_baselines.R",
    conf_level = conf_level,
    versions = versions,
    calls = calls
  ),
  cases = cases
)

jsonlite::write_json(out, out_path, pretty = TRUE, auto_unbox = TRUE, digits = NA, null = "null")
cat("Wrote", out_path, "\n")
