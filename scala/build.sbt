name := "cinalogic"
version := "1.0"
scalaVersion := "2.13.12"

libraryDependencies ++= Seq(
  "org.json4s" %% "json4s-native" % "4.0.7"
)

assembly / assemblyMergeStrategy := {
  case PathList("META-INF", _*) => MergeStrategy.discard
  case _                        => MergeStrategy.first
}
